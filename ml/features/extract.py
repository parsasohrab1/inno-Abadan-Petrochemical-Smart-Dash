"""Feature extraction from a vibration/acoustic signal frame (FR-06, FR-07).

- FFT with a Hann window (FR-06)
- Time-domain statistical features: RMS, Peak, Crest, Kurtosis, Skewness, Shape/Clearance (FR-07)
- Amplitude at multiples of the rotation frequency (0.33X..10X) and fine band energy to separate bearing resonance
- Envelope analysis (envelope spectrum): peak at BPFO/BPFI/BSF/FTF and sidebands — the key to
  separating the four bearing faults from each other and from other faults
- Dedicated indicators: line frequency (50/100 Hz), spectral flatness (cavitation),
  mid-band sharpness (resonance), belt harmonic series, oil whirl tone, gear mesh frequency
"""
from __future__ import annotations

import numpy as np
from scipy.signal import hilbert
from scipy.stats import kurtosis, skew

from services.common.domain.faults import (
    BEARING_BPFI,
    BEARING_BPFO,
    BEARING_BSF,
    BEARING_FTF,
)

ORDERS = [0.33, 0.42, 0.5, 0.84, 1.0, 1.26, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0]

# fine bands (Hz) to separate the bearing-fault carrier resonance frequency and resonance
BANDS: dict[str, tuple[float, float]] = {
    "be_0_500": (0, 500),
    "be_500_1500": (500, 1500),
    "be_1500_2500": (1500, 2500),
    "be_2500_3500": (2500, 3500),
    "be_3500_4500": (3500, 4500),
    "be_4500_6000": (4500, 6000),
    "be_6000_9000": (6000, 9000),
    "be_9000_13000": (9000, 13000),
}


def _hann_fft(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    w = np.hanning(len(x))
    xw = (x - x.mean()) * w
    spec = np.abs(np.fft.rfft(xw)) / (np.sum(w) / 2.0)
    freqs = np.fft.rfftfreq(len(x), d=1.0 / fs)
    return freqs, spec


def _peak_near(freqs: np.ndarray, spec: np.ndarray, target_hz: float, tol_hz: float) -> float:
    if target_hz <= 0 or target_hz >= freqs[-1]:
        return 0.0
    mask = np.abs(freqs - target_hz) <= tol_hz
    return float(spec[mask].max()) if mask.any() else 0.0


def envelope_spectrum(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    """Envelope spectrum: FFT of the absolute value of the signal's Hilbert transform (standard bearing-fault analysis)."""
    env = np.abs(hilbert(x - x.mean()))
    env = env - env.mean()
    w = np.hanning(len(env))
    es = np.abs(np.fft.rfft(env * w)) / (np.sum(w) / 2.0)
    ef = np.fft.rfftfreq(len(env), d=1.0 / fs)
    return ef, es


def order_amplitudes(
    freqs: np.ndarray, spec: np.ndarray, f0: float, tol_hz: float
) -> dict[str, float]:
    out: dict[str, float] = {}
    for o in ORDERS:
        out[f"ord_{o:g}x"] = _peak_near(freqs, spec, o * f0, tol_hz)
    return out


def band_energy(freqs: np.ndarray, spec: np.ndarray) -> dict[str, float]:
    p = spec**2
    total = float(p[freqs > 5].sum()) + 1e-12
    out: dict[str, float] = {}
    for name, (lo, hi) in BANDS.items():
        e = float(p[(freqs >= lo) & (freqs < hi)].sum())
        out[name] = e / total  # relative → independent of absolute amplitude
    return out


def extract_features(x: np.ndarray, fs: float, rpm: float | None) -> dict[str, float]:
    x = np.asarray(x, dtype=float)
    rms = float(np.sqrt(np.mean(x**2))) or 1e-9
    peak = float(np.max(np.abs(x)))
    abs_mean = float(np.mean(np.abs(x))) or 1e-9
    feats: dict[str, float] = {
        "rms": rms,
        "peak": peak,
        "peak_to_peak": float(np.ptp(x)),
        "crest_factor": peak / rms,
        "kurtosis": float(kurtosis(x, fisher=True)),
        "skewness": float(skew(x)),
        "shape_factor": rms / abs_mean,
        "clearance_factor": peak / (float(np.mean(np.sqrt(np.abs(x)))) ** 2 or 1e-9),
        "impulse_factor": peak / abs_mean,
    }

    freqs, spec = _hann_fft(x, fs)
    feats.update(band_energy(freqs, spec))
    feats["spectral_centroid"] = float(np.sum(freqs * spec) / (np.sum(spec) or 1e-9))
    sp = spec[freqs > 20] + 1e-12
    feats["spectral_flatness"] = float(np.exp(np.mean(np.log(sp))) / np.mean(sp))
    mid = spec[(freqs > 1200) & (freqs < 3000)]
    feats["mid_band_peakiness"] = float(mid.max() / (np.median(mid) + 1e-12)) if mid.size else 0.0
    feats["hf_energy_ratio"] = (
        feats["be_4500_6000"] + feats["be_6000_9000"] + feats["be_9000_13000"]
    )

    # line frequency (speed-independent) — electrical fault
    feats["line_50hz"] = _peak_near(freqs, spec, 50.0, 1.5) / rms
    feats["line_100hz"] = _peak_near(freqs, spec, 100.0, 1.5) / rms

    # Hilbert envelope
    env = np.abs(hilbert(x - x.mean()))
    feats["envelope_kurtosis"] = float(kurtosis(env, fisher=True))

    if rpm and rpm > 0:
        f0 = rpm / 60.0
        tol = max(2.0, 0.015 * f0)
        orders = order_amplitudes(freqs, spec, f0, tol)
        feats.update(orders)
        one_x = orders.get("ord_1x", 1e-9) or 1e-9
        feats["ratio_2x_1x"] = orders.get("ord_2x", 0.0) / one_x
        feats["ratio_3x_1x"] = orders.get("ord_3x", 0.0) / one_x
        feats["sub_synchronous"] = orders.get("ord_0.5x", 0.0) / one_x
        feats["half_order_sum"] = (
            orders.get("ord_0.5x", 0)
            + orders.get("ord_1.5x", 0)
            + orders.get("ord_2.5x", 0)
            + orders.get("ord_3.5x", 0)
        ) / one_x
        feats["harmonic_sum"] = sum(
            orders.get(f"ord_{o:g}x", 0) for o in (1.0, 2.0, 3.0, 4.0, 5.0)
        ) / one_x

        # oil whirl: ~0.45X tone without a second harmonic
        ow = _peak_near(freqs, spec, 0.44 * f0, 0.06 * f0)
        feats["oil_whirl_ratio"] = ow / one_x
        feats["oil_whirl_no_harmonic"] = ow / (_peak_near(freqs, spec, 0.88 * f0, tol) + 1e-9)

        # belt: sub-synchronous harmonic series
        feats["belt_series"] = (
            _peak_near(freqs, spec, 0.42 * f0, tol)
            + _peak_near(freqs, spec, 0.84 * f0, tol)
            + _peak_near(freqs, spec, 1.26 * f0, tol)
        ) / one_x

        # gear mesh
        feats["gmf_ratio"] = (
            _peak_near(freqs, spec, 18 * f0, 3 * tol)
            + _peak_near(freqs, spec, 36 * f0, 3 * tol)
        ) / one_x

        # --- envelope spectrum: peak at the characteristic bearing frequencies ---
        ef, es = envelope_spectrum(x, fs)
        es_rms = float(np.sqrt(np.mean(es[ef < 2000] ** 2))) + 1e-12
        etol = max(2.0, 0.02 * f0)

        def envn(order: float) -> float:
            return _peak_near(ef, es, order * f0, etol) / es_rms

        feats["env_bpfo"] = envn(BEARING_BPFO) + 0.5 * envn(2 * BEARING_BPFO)
        feats["env_bpfi"] = envn(BEARING_BPFI) + 0.5 * envn(2 * BEARING_BPFI)
        feats["env_bsf"] = envn(2 * BEARING_BSF) + 0.5 * envn(4 * BEARING_BSF)
        feats["env_ftf"] = envn(BEARING_FTF) + envn(2 * BEARING_FTF) + envn(3 * BEARING_FTF)
        feats["env_1x"] = envn(1.0)
        feats["env_bpfi_sidebands"] = (
            _peak_near(ef, es, (BEARING_BPFI - 1.0) * f0, etol)
            + _peak_near(ef, es, (BEARING_BPFI + 1.0) * f0, etol)
        ) / es_rms
        feats["env_bsf_sidebands"] = (
            _peak_near(ef, es, (2 * BEARING_BSF - BEARING_FTF) * f0, etol)
            + _peak_near(ef, es, (2 * BEARING_BSF + BEARING_FTF) * f0, etol)
        ) / es_rms
        lowband = es[(ef > 0.5) & (ef < 6.0)]
        feats["env_pole_pass"] = float(lowband.max()) / es_rms if lowband.size else 0.0

    return {k: (0.0 if not np.isfinite(v) else round(float(v), 6)) for k, v in feats.items()}


# fixed order of the feature vector for the ML model
FEATURE_ORDER: list[str] = [
    "rms", "peak", "peak_to_peak", "crest_factor", "kurtosis", "skewness",
    "shape_factor", "clearance_factor", "impulse_factor",
    *BANDS.keys(),
    "spectral_centroid", "spectral_flatness", "mid_band_peakiness", "hf_energy_ratio",
    "line_50hz", "line_100hz", "envelope_kurtosis",
    *[f"ord_{o:g}x" for o in ORDERS],
    "ratio_2x_1x", "ratio_3x_1x", "sub_synchronous", "half_order_sum", "harmonic_sum",
    "oil_whirl_ratio", "oil_whirl_no_harmonic", "belt_series", "gmf_ratio",
    "env_bpfo", "env_bpfi", "env_bsf", "env_ftf", "env_1x",
    "env_bpfi_sidebands", "env_bsf_sidebands", "env_pole_pass",
]


def to_vector(feats: dict[str, float]) -> np.ndarray:
    return np.array([feats.get(k, 0.0) for k in FEATURE_ORDER], dtype=np.float32)
