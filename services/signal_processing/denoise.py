"""Noise filtering before feature extraction — detrending, band-pass, Wavelet thresholding."""
from __future__ import annotations

import numpy as np
import pywt
from scipy.signal import butter, detrend, sosfiltfilt


def bandpass(x: np.ndarray, fs: float, lo: float = 5.0, hi: float | None = None) -> np.ndarray:
    hi = hi or (0.45 * fs)
    sos = butter(4, [lo, hi], btype="band", fs=fs, output="sos")
    return sosfiltfilt(sos, x)


def wavelet_denoise(x: np.ndarray, wavelet: str = "db8", level: int = 4) -> np.ndarray:
    coeffs = pywt.wavedec(x, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    uthresh = sigma * np.sqrt(2 * np.log(len(x)))
    coeffs[1:] = [pywt.threshold(c, uthresh, mode="soft") for c in coeffs[1:]]
    out = pywt.waverec(coeffs, wavelet)
    return out[: len(x)]


def clean(x: np.ndarray, fs: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    x = detrend(x, type="linear")
    x = bandpass(x, fs)
    if len(x) >= 64:
        x = wavelet_denoise(x)
    return x
