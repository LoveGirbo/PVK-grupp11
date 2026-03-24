#!/usr/bin/env python3
import argparse
import queue
import sys
import threading
import time
from typing import Optional, List

import numpy as np
import sounddevice as sd


def int_or_str(text: str):
    try:
        return int(text)
    except ValueError:
        return text


def rms_dbfs(x: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(x * x)))
    return 20.0 * np.log10(rms + 1e-12)


def next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def dominant_freq_hz(block: np.ndarray, samplerate: int, nfft: Optional[int], min_hz: float) -> float:
    """Dominant frequency (FFT peak) for one block. Returns NaN if unreliable."""
    x = block.astype(np.float64, copy=False)
    x = x - np.mean(x)  # remove DC

    N = len(x)
    if N < 8:
        return float("nan")

    if nfft is None:
        nfft = next_pow2(N)

    window = np.hanning(N)
    X = np.fft.rfft(x * window, n=nfft)
    mag = np.abs(X)
    freqs = np.fft.rfftfreq(nfft, d=1.0 / samplerate)

    # ignore DC and anything below min_hz
    valid = freqs >= max(min_hz, 1e-9)
    mag = mag[valid]
    freqs = freqs[valid]

    if mag.size == 0 or np.all(mag == 0):
        return float("nan")

    return float(freqs[int(np.argmax(mag))])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--list-devices", action="store_true", help="list audio devices and exit")
    parser.add_argument("-d", "--device", type=int_or_str, default=None, help="input device (ID or substring)")
    parser.add_argument("-c", "--channels", type=int, default=1, help="number of input channels (default: 1)")
    parser.add_argument("-r", "--samplerate", type=float, default=None, help="sampling rate (default: device default)")
    parser.add_argument("-b", "--blocksize", type=int, default=1024, help="block size in samples (default: 1024)")

    parser.add_argument("-t", "--threshold", type=float, default=-30.0,
                        help="trigger threshold in dBFS (default: -30)")
    parser.add_argument("-s", "--seconds", type=float, default=5.0,
                        help="measurement duration after trigger in seconds (default: 5)")
    parser.add_argument("--pause", type=float, default=7.0,
                        help="pause after each measurement before listening again (default: 7)")

    parser.add_argument("--gate-db", type=float, default=-40.0,
                        help="only compute frequency stats for blocks with RMS >= gate-db (default: -40)")
    parser.add_argument("--min-hz", type=float, default=20.0,
                        help="ignore frequencies below this (default: 20 Hz)")
    parser.add_argument("--fftsize", type=int, default=0,
                        help="FFT size (0=auto per block, otherwise e.g. 8192/16384/32768)")

    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices()) # Returns available listening devices
        return

    if args.samplerate is None:
        info = sd.query_devices(args.device, "input")
        args.samplerate = info["default_samplerate"]

    samplerate = int(args.samplerate)
    needed_samples = int(args.seconds * samplerate)

    # Message passing from audio thread -> main thread
    msg_q: "queue.Queue[dict]" = queue.Queue()

    # State machine
    LISTENING, MEASURING, COOLDOWN = 0, 1, 2
    state = LISTENING
    cooldown_until = 0.0

    # Measurement accumulators
    collected = 0
    sumsq = 0.0  # sum of squares for RMS over whole measurement
    max_block_db = -np.inf
    freqs_kept: List[float] = []
    nfft: Optional[int] = None if args.fftsize <= 0 else int(args.fftsize)

    lock = threading.Lock()

    def reset_measurement():
        nonlocal collected, sumsq, max_block_db, freqs_kept
        collected = 0
        sumsq = 0.0
        max_block_db = -np.inf
        freqs_kept = []

    def process_measure_block(mono: np.ndarray):
        """Consume as much as needed from this block into the 5s measurement."""
        nonlocal collected, sumsq, max_block_db, freqs_kept, state, cooldown_until

        if collected >= needed_samples:
            return

        remaining = needed_samples - collected
        x = mono[:remaining]  # trim last block if needed

        # dB (block RMS)
        block_db = rms_dbfs(x)
        if block_db > max_block_db:
            max_block_db = block_db

        # accumulate RMS over whole measurement
        sumsq += float(np.sum(x.astype(np.float64) * x.astype(np.float64)))
        collected += len(x)

        # frequency per block, but only if above gate
        if block_db >= args.gate_db:
            f = dominant_freq_hz(x, samplerate, nfft=nfft, min_hz=args.min_hz)
            if not np.isnan(f):
                freqs_kept.append(float(f))

        # If done, compute and publish results, enter cooldown
        if collected >= needed_samples:
            mean_rms = np.sqrt(sumsq / max(1, needed_samples))
            mean_db = 20.0 * np.log10(float(mean_rms) + 1e-12)

            if freqs_kept:
                low_f = float(np.min(freqs_kept))
                high_f = float(np.max(freqs_kept))
                mean_f = float(np.mean(freqs_kept))
                blocks_used = len(freqs_kept)
            else:
                low_f = high_f = mean_f = float("nan")
                blocks_used = 0

            msg_q.put({
                "type": "result",
                "max_db": float(max_block_db),
                "mean_db": float(mean_db),
                "low_f": low_f,
                "high_f": high_f,
                "mean_f": mean_f,
                "blocks_used": blocks_used,
                "gate_db": float(args.gate_db),
            })

            state = COOLDOWN
            cooldown_until = time.monotonic() + float(args.pause)

    def audio_callback(indata, frames, time_info, status):
        nonlocal state, cooldown_until

        if status:
            msg_q.put({"type": "status", "text": str(status)})

        mono = np.mean(indata, axis=1).copy()  # float32
        level_db = rms_dbfs(mono)

        now = time.monotonic()

        with lock:
            if state == COOLDOWN:
                if now >= cooldown_until:
                    state = LISTENING
                    msg_q.put({"type": "info", "text": "Listening again..."})
                else:
                    return  # ignore audio during pause

            if state == LISTENING:
                if level_db >= args.threshold:
                    reset_measurement()
                    state = MEASURING
                    msg_q.put({
                        "type": "trigger",
                        "text": f"TRIGGER: {level_db:.1f} dBFS >= {args.threshold:.1f} dBFS. Measuring {args.seconds:.1f}s..."
                    })
                    # include this block as the first measurement block
                    process_measure_block(mono)
            elif state == MEASURING:
                process_measure_block(mono)

    stream = sd.InputStream(
        device=args.device,
        channels=args.channels,
        samplerate=samplerate,
        blocksize=args.blocksize,
        callback=audio_callback,
    )

    print(f"Running. device={args.device}, samplerate={samplerate}, threshold={args.threshold} dBFS")
    print(f"Measurement={args.seconds}s, pause={args.pause}s, freq gate={args.gate_db} dBFS, min-hz={args.min_hz} Hz")
    print("Press Ctrl+C to stop.\n")

    try:
        with stream:
            while True:
                try:
                    msg = msg_q.get(timeout=0.2)
                except queue.Empty:
                    continue

                if msg["type"] == "status":
                    print(msg["text"], file=sys.stderr)

                elif msg["type"] in ("trigger", "info"):
                    print(msg["text"])

                elif msg["type"] == "result":
                    print("--- Measurement result ---")
                    print(f"max decibel:     {msg['max_db']:.2f} dBFS")
                    print(f"mean decibel:    {msg['mean_db']:.2f} dBFS")
                    print(f"freq blocks used (>= {msg['gate_db']:.1f} dBFS): {msg['blocks_used']}")
                    print(f"lowest freq:     {msg['low_f']:.2f} Hz")
                    print(f"highest freq:    {msg['high_f']:.2f} Hz")
                    print(f"mean freq:       {msg['mean_f']:.2f} Hz")
                    print(f"(pause {args.pause:.1f}s)\n")

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
