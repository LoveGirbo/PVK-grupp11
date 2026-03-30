import numpy as np
import sounddevice as sd
from collections import deque
from typing import Optional


def list_input_devices():
    devices = sd.query_devices()
    return [
        {
            "index": i,
            "name": str(d["name"]),
            "max_input_channels": int(d["max_input_channels"]),
            "default_samplerate": int(d["default_samplerate"]),
        }
        for i, d in enumerate(devices)
        if int(d["max_input_channels"]) > 0
    ]


def rms_dbfs(x: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(x * x)))
    return 20.0 * np.log10(rms + 1e-12)


def dominant_freq_hz(
    block: np.ndarray,
    samplerate: int,
    nfft: Optional[int],
    min_hz: float,
    max_hz: Optional[float],
) -> float:
    """
    Behåller samma namn som tidigare, men använder en enklare
    autokorrelationsmetod som ofta passar röster bättre.
    """
    x = block.astype(np.float64, copy=False)
    x = x - np.mean(x)

    if len(x) < 2:
        return float("nan")

    corr = np.correlate(x, x, mode="full")
    corr = corr[len(corr) // 2:]

    if max_hz is None:
        max_hz = samplerate / 2

    min_lag = max(1, int(samplerate / max_hz))
    max_lag = min(len(corr) - 1, int(samplerate / min_hz))

    if min_lag >= max_lag:
        return float("nan")

    region = corr[min_lag:max_lag + 1]
    if len(region) == 0:
        return float("nan")

    lag = min_lag + int(np.argmax(region))

    if lag <= 0:
        return float("nan")

    return float(samplerate / lag)


class SoundReader:
    def __init__(
        self,
        device=None,
        channels: int = 1,
        samplerate: Optional[float] = None,
        blocksize: int = 4096,
        gate_open_db: float = -38.0,
        gate_close_db: float = -42.0,
        min_hz: float = 20.0,
        max_hz: Optional[float] = 2000.0,
        fftsize: int = 16384,
        smoothing_alpha: float = 0.15,
        median_window_size: int = 5,
    ):
        self.device = device
        self.channels = channels
        self.blocksize = blocksize
        self.gate_open_db = gate_open_db
        self.gate_close_db = gate_close_db
        self.min_hz = min_hz
        self.max_hz = max_hz

        # Behålls för kompatibilitet, även om de inte används lika mycket längre
        self.nfft = None if fftsize <= 0 else int(fftsize)
        self.smoothing_alpha = float(smoothing_alpha)
        self.median_window_size = max(1, int(median_window_size))

        if samplerate is None:
            info = sd.query_devices(device, "input")
            samplerate = info["default_samplerate"]

        self.samplerate = int(samplerate)

        self.active = False
        self.latest_frequency: Optional[float] = None
        self.latest_db: Optional[float] = None
        self.smoothed_frequency: Optional[float] = None
        self.freq_history: deque[float] = deque(maxlen=self.median_window_size)
        self.gate_is_open = False

        self.stream = sd.InputStream(
            device=self.device,
            channels=self.channels,
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            callback=self._audio_callback,
        )

    def start(self):
        self.stream.start()

    def stop(self):
        if self.stream.active:
            self.stream.stop()
        self.stream.close()

    def start_listening(self):
        self.active = True
        self.latest_frequency = None
        self.latest_db = None
        self.smoothed_frequency = None
        self.freq_history.clear()
        self.gate_is_open = False

    def stop_listening(self):
        self.active = False
        self.latest_frequency = None
        self.latest_db = None
        self.smoothed_frequency = None
        self.freq_history.clear()
        self.gate_is_open = False

    def get_latest_frequency(self) -> Optional[float]:
        return self.latest_frequency

    def get_latest_db(self) -> Optional[float]:
        return self.latest_db

    def _update_gate(self, level_db: float) -> bool:
        if self.gate_is_open:
            if level_db < self.gate_close_db:
                self.gate_is_open = False
        else:
            if level_db >= self.gate_open_db:
                self.gate_is_open = True
        return self.gate_is_open

    def _audio_callback(self, indata, frames, time_info, status):
        mono = indata[:, 0].copy()
        level_db = rms_dbfs(mono)

        if not self.active:
            return

        self.latest_db = level_db

        if not self._update_gate(level_db):
            self.latest_frequency = None
            self.smoothed_frequency = None
            self.freq_history.clear()
            return

        freq = dominant_freq_hz(
            mono,
            samplerate=self.samplerate,
            nfft=self.nfft,
            min_hz=self.min_hz,
            max_hz=self.max_hz,
        )

        if np.isnan(freq) or freq <= 0:
            self.latest_frequency = None
            return

        self.freq_history.append(float(freq))
        median_freq = float(np.median(self.freq_history))

        if self.smoothed_frequency is None:
            self.smoothed_frequency = median_freq
        else:
            a = self.smoothing_alpha
            self.smoothed_frequency = a * median_freq + (1.0 - a) * self.smoothed_frequency

        self.latest_frequency = float(self.smoothed_frequency)