"""زنجیره‌ی وضعیت سلامت سنسور — README §۱۰-۲ (بازنویسی‌شده با مدل مارکوف صریح)."""
from __future__ import annotations

import numpy as np

from services.common.domain.enums import HealthColor
from services.common.domain.health import DeviceHealthInputs, evaluate_device_health

# ماتریس انتقال روزانه (green, yellow, red)
TRANSITION = {
    HealthColor.GREEN: [0.985, 0.012, 0.003],
    HealthColor.YELLOW: [0.10, 0.83, 0.07],
    HealthColor.RED: [0.03, 0.00, 0.97],  # تا تعویض در قرمز می‌ماند
}
_ORDER = [HealthColor.GREEN, HealthColor.YELLOW, HealthColor.RED]


def next_status(current: HealthColor, rng: np.random.Generator) -> HealthColor:
    return _ORDER[rng.choice(3, p=TRANSITION[current])]


def synth_health_metrics(status: HealthColor, rng: np.random.Generator) -> DeviceHealthInputs:
    """پارامترهای ۶‌گانه‌ی متناظر با وضعیت هدف (README §۵-۲)."""
    if status == HealthColor.GREEN:
        return DeviceHealthInputs(
            supply_voltage=24 + rng.normal(0, 0.3),
            loop_current_ma=float(rng.uniform(5, 19)),
            snr_db=float(rng.uniform(28, 50)),
            calibration_drift_pct=float(abs(rng.normal(0, 0.6))),
            comm_latency_ms=float(rng.uniform(20, 180)),
            comm_gap_s=0.0,
            device_temp_c=float(rng.uniform(30, 60)),
            days_since_calibration=float(rng.uniform(0, 80)),
        )
    if status == HealthColor.YELLOW:
        return DeviceHealthInputs(
            supply_voltage=24 + rng.choice([-1, 1]) * rng.uniform(1.3, 2.2),
            loop_current_ma=float(rng.uniform(4.0, 20.0)),
            snr_db=float(rng.uniform(13, 21)),
            calibration_drift_pct=float(rng.uniform(2.1, 4.8)),
            comm_latency_ms=float(rng.uniform(300, 900)),
            comm_gap_s=float(rng.uniform(0, 20)),
            device_temp_c=float(rng.uniform(60, 78)),
            days_since_calibration=float(rng.uniform(85, 175)),
        )
    return DeviceHealthInputs(  # RED
        supply_voltage=24 + rng.choice([-1, 1]) * rng.uniform(3.0, 6.0),
        loop_current_ma=float(rng.choice([rng.uniform(0, 3.4), rng.uniform(21, 24)])),
        snr_db=float(rng.uniform(2, 11)),
        calibration_drift_pct=float(rng.uniform(5.2, 12)),
        comm_latency_ms=float(rng.uniform(800, 4000)),
        comm_gap_s=float(rng.uniform(65, 600)),
        device_temp_c=float(rng.uniform(86, 110)),
        days_since_calibration=float(rng.uniform(120, 400)),
    )


def verify_rules_consistency(n: int = 2000, seed: int = 0) -> float:
    """نسبت مواردی که قانون رنگ با وضعیت هدف مولّد می‌خواند (کیفیت داده‌ی آموزش)."""
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n):
        target = _ORDER[int(rng.integers(0, 3))]
        got = evaluate_device_health(synth_health_metrics(target, rng)).status
        hits += int(got == target)
    return hits / n
