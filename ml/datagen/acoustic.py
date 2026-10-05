"""Synthetic acoustic signal — leak and friction detection (README §3-2, FR-10).

Gas/steam leak ⟵ high-frequency broadband noise (20–40 kHz) with a stable envelope.
Friction/cavitation ⟵ irregular pulses.
"""
from __future__ import annotations

import numpy as np


def synth_acoustic(
    fs: float = 48000.0,
    n: int = 8192,
    leak_severity: float = 0.0,
    friction_severity: float = 0.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    rng = rng or np.random.default_rng()
    t = np.arange(n) / fs
    x = 0.01 * rng.standard_normal(n)  # ambient noise
    x += 0.005 * np.sin(2 * np.pi * 120 * t)  # machinery hum

    if leak_severity > 0:
        hf = rng.standard_normal(n)
        # simple high-pass filter
        hf = np.convolve(hf, [1, -0.95], mode="same")
        x += (0.03 + 0.25 * leak_severity) * hf

    if friction_severity > 0:
        k = int(fs * 0.01)
        spikes = np.zeros(n)
        idx = rng.integers(0, n, size=int(5 + 40 * friction_severity))
        spikes[idx] = rng.uniform(0.5, 1.0, size=len(idx))
        decay = np.exp(-np.linspace(0, 6, k))
        x += (0.1 + 0.4 * friction_severity) * np.convolve(spikes, decay, mode="same")

    return x.astype(np.float32)


def leak_index(x: np.ndarray, fs: float) -> float:
    """Ratio of ultrasonic band energy to the total — a simple leak indicator."""
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1 / fs)
    total = float((spec**2).sum()) + 1e-9
    ultra = float((spec[freqs > 18000] ** 2).sum())
    return round(ultra / total, 4)
