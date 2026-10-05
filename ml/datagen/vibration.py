"""Synthetic vibration signal generation with fault injection — README §10-1 (rewritten and corrected).

`synth_waveform` builds an acceleration signal frame (g) in which the physical signature of a given fault with a given
severity is embedded. The basis of the signatures: `services.common.domain.faults.SIGNATURES`.

Each fault is rendered with a combination of these components so it can be distinguished in the raw spectrum and the envelope spectrum
(envelope spectrum):

* Discrete tones at multiples of 1X (unbalance, misalignment, looseness, belt …)
* Damped impact pulse trains that excite the structural resonance (bearing faults)
* Amplitude modulation to build sidebands (inner race ← 1X, ball ← FTF)
* Speed-independent tones (stator electrical fault ← 100 Hz)
* Absolute sideband around 1X (rotor bar break ← pole-pass ~1.6 Hz)
* Band-limited noise (cavitation, looseness)
* Waveform clipping (mechanical looseness, rotor rub)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfiltfilt

from services.common.domain.enums import FaultType
from services.common.domain.faults import (
    BEARING_BSF,
    BEARING_FTF,
    SIGNATURES,
)


@dataclass
class WaveformSpec:
    rpm: float = 2960.0
    fs: float = 25600.0          # sampling rate (FR-01: ≥ 25.6 kHz)
    n: int = 32768              # frame length (~1.28s → frequency resolution ~0.78 Hz for the pole-pass sideband)
    base_g: float = 0.05        # base healthy vibration amplitude (approx. g RMS)
    noise_g: float = 0.008


def _bandlimited_noise(
    n: int, fs: float, lo: float, hi: float, rng: np.random.Generator
) -> np.ndarray:
    white = rng.standard_normal(n)
    nyq = fs / 2.0
    lo = max(1.0, lo)
    hi = min(nyq * 0.98, hi)
    if hi <= lo:
        return white
    sos = butter(4, [lo / nyq, hi / nyq], btype="band", output="sos")
    filtered = sosfiltfilt(sos, white)
    return filtered / (np.std(filtered) + 1e-12)


def _impulse_train(
    t: np.ndarray,
    fs: float,
    defect_hz: float,
    carrier_hz: float,
    amp: float,
    rng: np.random.Generator,
    mod_hz: float | None = None,
    mod_depth: float = 0.0,
    damping: float = 900.0,
) -> np.ndarray:
    """Damped impact pulse train at the fault frequency that excites the carrier_hz resonance."""
    n = len(t)
    sig = np.zeros(n)
    if defect_hz <= 0 or carrier_hz is None or carrier_hz <= 0:
        return sig
    period = fs / defect_hz
    if period < 4:
        return sig
    ring_len = int(min(n, fs * 0.03))
    tr = np.arange(ring_len) / fs
    ring = np.exp(-damping * tr) * np.sin(2 * np.pi * carrier_hz * tr)
    pos = rng.uniform(0, period)
    while pos < n:
        i = int(pos)
        a = amp
        if mod_hz:
            a *= 1.0 + mod_depth * np.sin(2 * np.pi * mod_hz * i / fs)
        end = min(n, i + ring_len)
        sig[i:end] += a * ring[: end - i]
        pos += period * (1.0 + rng.normal(0.0, 0.018))
    return sig


def synth_waveform(
    fault: FaultType,
    severity: float,
    spec: WaveformSpec | None = None,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """severity ∈ [0,1]. Output: acceleration array in g with length spec.n."""
    spec = spec or WaveformSpec()
    rng = rng or np.random.default_rng()
    sev = float(np.clip(severity, 0.0, 1.0))

    n, fs = spec.n, spec.fs
    t = np.arange(n) / fs
    f0 = spec.rpm / 60.0
    nyq = fs / 2.0

    def tone(freq: float, amp: float) -> np.ndarray:
        if freq <= 0 or freq >= nyq:
            return np.zeros(n)
        return amp * np.sin(2 * np.pi * freq * t + rng.uniform(0, 2 * np.pi))

    # --- healthy component: 1X + small harmonics ---
    sig = tone(f0, spec.base_g)
    sig += tone(2 * f0, 0.4 * spec.base_g)
    sig += tone(3 * f0, 0.18 * spec.base_g)

    if fault != FaultType.NORMAL:
        s = SIGNATURES[fault]
        gain = spec.base_g * (0.5 + 4.0 * sev)

        # 1) Discrete tones at multiples of 1X
        weights = s.spectral_weights or (1.0,) * len(s.spectral_orders)
        use_tone_mod = s.modulation_order is not None and not s.envelope_orders
        for order, w in zip(s.spectral_orders, weights, strict=False):
            comp = tone(order * f0, gain * w)
            if use_tone_mod:
                comp = comp * (
                    1.0 + 0.5 * np.sin(2 * np.pi * s.modulation_order * f0 * t)
                )
            sig += comp

        # 2) Speed-independent tones (electrical fault)
        for fx in s.fixed_hz:
            sig += tone(fx, gain * 1.4)

        # 3) Absolute sideband around 1X + slow AM (rotor bar break, pole-pass)
        if s.sideband_hz:
            sig += tone(f0 - s.sideband_hz, gain * 0.6)
            sig += tone(f0 + s.sideband_hz, gain * 0.6)
            sig *= 1.0 + 0.2 * sev * np.sin(2 * np.pi * 2 * s.sideband_hz * t)

        # 4) Bearing faults: impact pulse train + modulation
        if s.envelope_orders and s.carrier_hz:
            mod_hz = s.modulation_order * f0 if s.modulation_order else None
            for k, eo in enumerate(s.envelope_orders):
                sig += _impulse_train(
                    t, fs, eo * f0, s.carrier_hz, gain * 3.2 * (0.65**k), rng,
                    mod_hz=mod_hz, mod_depth=s.modulation_depth,
                )

        # 5) Resonance: a narrow high-Q peak at a fixed frequency (speed-independent)
        if fault == FaultType.RESONANCE and s.carrier_hz:
            nb = _bandlimited_noise(n, fs, s.carrier_hz - 12, s.carrier_hz + 12, rng)
            sig += gain * 3.0 * nb + tone(s.carrier_hz, gain * 2.2)

        # 6) Oil whirl: an unstable tone ~0.45X with frequency wandering, no harmonics
        if fault == FaultType.OIL_WHIRL:
            fw = (0.42 + 0.05 * rng.random()) * f0
            wander = 1.0 + 0.008 * np.cumsum(rng.standard_normal(n)) / np.sqrt(n)
            sig += gain * 3.2 * np.sin(2 * np.pi * fw * t * wander)

        # 7) Band-limited noise
        if s.broadband_hz and s.broadband_hz != (0.0, 0.0):
            lo, hi = s.broadband_hz
            factor = 1.4 if fault == FaultType.CAVITATION else 0.35
            sig += gain * factor * _bandlimited_noise(n, fs, lo, hi, rng)

        # 8) Waveform: asymmetric clipping for looseness/rub
        if s.waveform_shape == "clipped":
            clip = np.max(np.abs(sig)) * (0.85 - 0.3 * sev)
            sig = np.clip(sig, -clip, clip * 1.7)

    sig += spec.noise_g * rng.standard_normal(n)
    return sig.astype(np.float32)


def degrade_severity(hours_since_onset: float, ttf_hours: float) -> float:
    """Fault growth curve: slow exponential at the start, steep at the end (like real CBM)."""
    if ttf_hours <= 0:
        return 1.0
    x = np.clip(hours_since_onset / ttf_hours, 0.0, 1.0)
    return float(x**2.2)


__all__ = ["WaveformSpec", "synth_waveform", "degrade_severity", "BEARING_BSF", "BEARING_FTF"]
