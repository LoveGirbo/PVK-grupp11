import threading
from typing import Optional

import numpy as np
import sounddevice as sd


def list_input_devices():
    devices = sd.query_devices()
    microphones = []

    for index, info in enumerate(devices):
        if int(info["max_input_channels"]) > 0:
            microphones.append(
                {
                    "index": index,
                    "name": str(info["name"]),
                    "max_input_channels": int(info["max_input_channels"]),
                    "default_samplerate": int(info["default_samplerate"]),
                }
            )

    return microphones


def rms_dbfs(x: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(x * x)))
    return 20.0 * np.log10(rms + 1e-12)


def next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def dominant_freq_hz(
    block: np.ndarray,
    samplerate: int,
    nfft: Optional[int],
    min_hz: float,
) -> float:
    x = block.astype(np.float64, copy=False)
    x = x - np.mean(x)

    n_samples = len(x)
    if n_samples < 8:
        return float("nan")

    if nfft is None:
        nfft = next_pow2(n_samples)

    if nfft < n_samples:
        nfft = next_pow2(n_samples)

    window = np.hanning(n_samples)
    spectrum = np.fft.rfft(x * window, n=nfft)
    magnitude = np.abs(spectrum)
    freqs = np.fft.rfftfreq(nfft, d=1.0 / samplerate)

    valid = freqs >= max(min_hz, 1e-9)
    magnitude = magnitude[valid]
    freqs = freqs[valid]

    if magnitude.size < 3 or np.all(magnitude <= 0):
        return float("nan")

    peak = int(np.argmax(magnitude))

    if peak == 0 or peak == len(magnitude) - 1:
        return float(freqs[peak])

    alpha = magnitude[peak - 1]
    beta = magnitude[peak]
    gamma = magnitude[peak + 1]

    denom = alpha - 2.0 * beta + gamma
    if denom == 0.0:
        return float(freqs[peak])

    p = 0.5 * (alpha - gamma) / denom
    bin_width = freqs[1] - freqs[0]

    return float(freqs[peak] + p * bin_width)


class SoundReader:
    def __init__(
        self,
        device=None,
        channels: int = 1,
        samplerate: Optional[float] = None,
        blocksize: int = 16384,
        gate_db: float = -40.0,
        min_hz: float = 20.0,
        fftsize: int = 32768,
    ):
        self.device = device
        self.channels = channels
        self.blocksize = blocksize
        self.gate_db = gate_db
        self.min_hz = min_hz
        self.nfft = None if fftsize <= 0 else int(fftsize)

        if samplerate is None:
            info = sd.query_devices(device, "input")
            samplerate = info["default_samplerate"]

        self.samplerate = int(samplerate)

        self.lock = threading.Lock()
        self.active = False
        self.latest_frequency: Optional[float] = None
        self.latest_db: Optional[float] = None

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
        with self.lock:
            self.active = True
            self.latest_frequency = None
            self.latest_db = None

    def stop_listening(self):
        with self.lock:
            self.active = False
            self.latest_frequency = None
            self.latest_db = None

    def get_latest_frequency(self) -> Optional[float]:
        with self.lock:
            return self.latest_frequency

    def get_latest_db(self) -> Optional[float]:
        with self.lock:
            return self.latest_db

    def _audio_callback(self, indata, frames, time_info, status):
        mono = indata[:, 0].copy()
        level_db = rms_dbfs(mono)

        with self.lock:
            if not self.active:
                return

            self.latest_db = level_db

            if level_db < self.gate_db:
                self.latest_frequency = None
                return

            freq = dominant_freq_hz(
                mono,
                samplerate=self.samplerate,
                nfft=self.nfft,
                min_hz=self.min_hz,
            )

            if np.isnan(freq):
                self.latest_frequency = None
            else:
                self.latest_frequency = float(freq)