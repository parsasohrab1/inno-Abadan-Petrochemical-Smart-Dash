"""تولید سیگنال ارتعاش سنتتیک با تزریق عیب — README §۱۰-۱ (بازنویسی و اصلاح‌شده).

تابع اصلی `synth_waveform` یک قاب سیگنال شتاب (g) تولید می‌کند که امضای فرکانسی
عیب مشخص با شدت داده‌شده در آن نشسته است. مبنای امضاها: `services.common.domain.faults`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from services.common.domain.enums import FaultType
from services.common.domain.faults import BEARING_FTF, SIGNATURES


@dataclass
class WaveformSpec:
    rpm: float = 2960.0
    fs: float = 25600.0          # نرخ نمونه‌برداری (FR-01: ≥ ۲۵.۶ kHz)
    n: int = 8192               # طول قاب
    base_g: float = 0.05        # دامنه‌ی ارتعاش پایه‌ی سالم (g RMS تقریبی)
    noise_g: float = 0.01


def synth_waveform(
    fault: FaultType,
    severity: float,
    spec: WaveformSpec | None = None,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """severity ∈ [0,1]. خروجی: آرایه‌ی شتاب بر حسب g با طول spec.n."""
    spec = spec or WaveformSpec()
    rng = rng or np.random.default_rng()
    sev = float(np.clip(severity, 0.0, 1.0))

    t = np.arange(spec.n) / spec.fs
    f0 = spec.rpm / 60.0

    # --- مؤلفه‌ی سالم: 1X با هارمونیک‌های کوچک ---
    sig = spec.base_g * np.sin(2 * np.pi * f0 * t + rng.uniform(0, 2 * np.pi))
    sig += 0.4 * spec.base_g * np.sin(2 * np.pi * 2 * f0 * t + rng.uniform(0, 2 * np.pi))
    sig += 0.2 * spec.base_g * np.sin(2 * np.pi * 3 * f0 * t + rng.uniform(0, 2 * np.pi))

    if fault != FaultType.NORMAL:
        s = SIGNATURES[fault]
        amp = spec.base_g * (0.6 + 3.5 * sev)

        for order in s.dominant_orders:
            fo = order * f0
            if fo >= spec.fs / 2:
                continue
            comp = amp * np.sin(2 * np.pi * fo * t + rng.uniform(0, 2 * np.pi))
            # یاتاقان: پالس‌های ضربه‌ای مدوله‌شده به‌جای تن خالص
            if fault.value.startswith("bearing"):
                env = np.zeros_like(t)
                period = int(spec.fs / fo) if fo > 0 else spec.n
                if period > 0:
                    idx = np.arange(0, spec.n, period)
                    env[idx % spec.n] = 1.0
                    decay = np.exp(-np.linspace(0, 8, min(period, spec.n)))
                    env = np.convolve(env, decay, mode="same")
                ftf = BEARING_FTF * f0
                mod = 1.0 + 0.5 * np.sin(2 * np.pi * ftf * t)
                comp = amp * 4 * env * mod * np.sin(2 * np.pi * 4500 * t)  # رزونانس یاتاقان
            sig += comp

        if s.broadband:
            sig += (0.5 * amp) * rng.standard_normal(spec.n)

        # لقی/سایش: بریدگی موج (کلیپینگ نامتقارن)
        if fault in {FaultType.MECHANICAL_LOOSENESS, FaultType.ROTOR_RUB}:
            clip = np.max(np.abs(sig)) * (0.9 - 0.3 * sev)
            sig = np.clip(sig, -clip, clip * 1.6)

    sig += spec.noise_g * rng.standard_normal(spec.n)
    return sig.astype(np.float32)


def degrade_severity(hours_since_onset: float, ttf_hours: float) -> float:
    """منحنی رشد عیب: نمایی کند در آغاز، تند در انتها (شبیه واقعیت CBM)."""
    if ttf_hours <= 0:
        return 1.0
    x = np.clip(hours_since_onset / ttf_hours, 0.0, 1.0)
    return float(x**2.2)
