"""استخراج ویژگی از قاب سیگنال ارتعاش/صوت (FR-06، FR-07).

- FFT با پنجره‌ی Hann (FR-06)
- ویژگی‌های آماری: RMS, Peak, Crest Factor, Kurtosis, Skewness, Shape Factor (FR-07)
- انرژی باندی و دامنه در مضارب فرکانس چرخش (0.5X..10X) برای تشخیص عیب
- شاخص‌های یاتاقان: کورتوزیس پاکت هیلبرت، انرژی فرکانس بالا
"""
from __future__ import annotations

import numpy as np
from scipy.signal import hilbert
from scipy.stats import kurtosis, skew

ORDERS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]


def _hann_fft(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    w = np.hanning(len(x))
    xw = (x - x.mean()) * w
    spec = np.abs(np.fft.rfft(xw)) / (np.sum(w) / 2.0)
    freqs = np.fft.rfftfreq(len(x), d=1.0 / fs)
    return freqs, spec


def order_amplitudes(freqs: np.ndarray, spec: np.ndarray, f0: float, tol_hz: float = 3.0) -> dict[str, float]:
    out: dict[str, float] = {}
    for o in ORDERS:
        target = o * f0
        mask = np.abs(freqs - target) <= tol_hz
        out[f"ord_{o:g}x"] = float(spec[mask].max()) if mask.any() else 0.0
    return out


def band_energy(freqs: np.ndarray, spec: np.ndarray) -> dict[str, float]:
    bands = {"be_0_1k": (0, 1000), "be_1k_5k": (1000, 5000), "be_5k_12k": (5000, 12000)}
    p = spec**2
    return {
        name: float(p[(freqs >= lo) & (freqs < hi)].sum())
        for name, (lo, hi) in bands.items()
    }


def extract_features(x: np.ndarray, fs: float, rpm: float | None) -> dict[str, float]:
    x = np.asarray(x, dtype=float)
    rms = float(np.sqrt(np.mean(x**2))) or 1e-9
    peak = float(np.max(np.abs(x)))
    feats: dict[str, float] = {
        "rms": rms,
        "peak": peak,
        "peak_to_peak": float(np.ptp(x)),
        "crest_factor": peak / rms,
        "kurtosis": float(kurtosis(x, fisher=True)),
        "skewness": float(skew(x)),
        "shape_factor": rms / (float(np.mean(np.abs(x))) or 1e-9),
        "clearance_factor": peak / (float(np.mean(np.sqrt(np.abs(x)))) ** 2 or 1e-9),
    }

    freqs, spec = _hann_fft(x, fs)
    feats.update(band_energy(freqs, spec))
    feats["spectral_centroid"] = float(np.sum(freqs * spec) / (np.sum(spec) or 1e-9))

    # پاکت هیلبرت برای عیوب یاتاقان
    env = np.abs(hilbert(x - x.mean()))
    feats["envelope_kurtosis"] = float(kurtosis(env, fisher=True))
    feats["hf_energy_ratio"] = feats["be_5k_12k"] / (
        feats["be_0_1k"] + feats["be_1k_5k"] + feats["be_5k_12k"] + 1e-9
    )

    if rpm and rpm > 0:
        f0 = rpm / 60.0
        orders = order_amplitudes(freqs, spec, f0)
        feats.update(orders)
        one_x = orders.get("ord_1x", 1e-9) or 1e-9
        feats["ratio_2x_1x"] = orders.get("ord_2x", 0.0) / one_x
        feats["ratio_3x_1x"] = orders.get("ord_3x", 0.0) / one_x
        feats["sub_synchronous"] = orders.get("ord_0.5x", 0.0) / one_x
        feats["half_order_sum"] = (
            orders.get("ord_0.5x", 0) + orders.get("ord_1.5x", 0) + orders.get("ord_2.5x", 0)
        ) / one_x

    return {k: (0.0 if not np.isfinite(v) else round(float(v), 6)) for k, v in feats.items()}


# ترتیب ثابت بردار ویژگی برای مدل ML
FEATURE_ORDER: list[str] = [
    "rms", "peak", "peak_to_peak", "crest_factor", "kurtosis", "skewness",
    "shape_factor", "clearance_factor", "be_0_1k", "be_1k_5k", "be_5k_12k",
    "spectral_centroid", "envelope_kurtosis", "hf_energy_ratio",
    *[f"ord_{o:g}x" for o in ORDERS],
    "ratio_2x_1x", "ratio_3x_1x", "sub_synchronous", "half_order_sum",
]


def to_vector(feats: dict[str, float]) -> np.ndarray:
    return np.array([feats.get(k, 0.0) for k in FEATURE_ORDER], dtype=np.float32)
