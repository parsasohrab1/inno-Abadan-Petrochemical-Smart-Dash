"""Health monitoring logic — green/yellow/red three-light for sensor, camera and equipment.

- Sensor/camera: based on the 6 parameters of README §5-2.
- Equipment: based on the health index 0..100 (README §4-1).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.common.domain.enums import HealthColor


@dataclass
class DeviceHealthInputs:
    supply_voltage: float = 24.0          # V   (allowed: 24 ± 5% green, ± 10% yellow)
    loop_current_ma: float = 12.0         # mA  (allowed: 4..20)
    snr_db: float = 40.0                  # dB
    calibration_drift_pct: float = 0.0    # % deviation from reference
    comm_latency_ms: float = 50.0         # ms
    comm_gap_s: float = 0.0               # seconds since last data
    device_temp_c: float = 40.0           # °C
    device_temp_limit_c: float = 85.0
    days_since_calibration: float = 10.0


@dataclass
class HealthResult:
    status: HealthColor
    reasons: list[str] = field(default_factory=list)


def evaluate_device_health(x: DeviceHealthInputs) -> HealthResult:
    """Default rule; can be overridden in `infra/postgres` or the rules file."""
    red: list[str] = []
    yellow: list[str] = []

    # 1 supply voltage
    dv = abs(x.supply_voltage - 24.0) / 24.0
    if dv > 0.10:
        red.append(f"Supply voltage {x.supply_voltage:.1f}V outside ±10%")
    elif dv > 0.05:
        yellow.append(f"Supply voltage {x.supply_voltage:.1f}V outside ±5%")

    # 2 output signal 4-20mA
    if not (3.6 <= x.loop_current_ma <= 20.5):
        red.append(f"Loop current {x.loop_current_ma:.1f}mA outside 4..20")
    elif not (4.0 <= x.loop_current_ma <= 20.0):
        yellow.append(f"Loop current {x.loop_current_ma:.1f}mA at the saturation boundary")

    # 3 signal quality (SNR)
    if x.snr_db < 12:
        red.append(f"Low SNR {x.snr_db:.0f}dB")
    elif x.snr_db < 20:
        yellow.append(f"Weak SNR {x.snr_db:.0f}dB")

    # 4 measurement accuracy (calibration drift)
    if x.calibration_drift_pct > 5:
        red.append(f"Calibration drift {x.calibration_drift_pct:.1f}%")
    elif x.calibration_drift_pct > 2:
        yellow.append(f"Calibration drift {x.calibration_drift_pct:.1f}%")

    # 5 communication
    if x.comm_gap_s > 60:
        red.append(f"Communication lost {x.comm_gap_s:.0f}s")
    elif x.comm_latency_ms > 500 or x.comm_gap_s > 10:
        yellow.append("High communication delay")

    # 6 sensor operating temperature
    if x.device_temp_c > x.device_temp_limit_c:
        red.append(f"Sensor temperature {x.device_temp_c:.0f}°C beyond the limit")
    elif x.device_temp_c > x.device_temp_limit_c - 10:
        yellow.append("Sensor temperature near the allowed limit")

    # expired calibration
    if x.days_since_calibration > 180:
        red.append("Calibration older than 180 days")
    elif x.days_since_calibration > 90:
        yellow.append("Calibration older than 90 days")

    if red:
        return HealthResult(HealthColor.RED, red + yellow)
    if yellow:
        return HealthResult(HealthColor.YELLOW, yellow)
    return HealthResult(HealthColor.GREEN, ["Normal operation"])


# equipment color thresholds based on the health index (configurable)
EQUIPMENT_GREEN_MIN = 75.0
EQUIPMENT_YELLOW_MIN = 45.0


def equipment_color(health_score: float) -> HealthColor:
    if health_score >= EQUIPMENT_GREEN_MIN:
        return HealthColor.GREEN
    if health_score >= EQUIPMENT_YELLOW_MIN:
        return HealthColor.YELLOW
    return HealthColor.RED


def health_score_from(severity: float, rul_hours: float, rul_reference_hours: float = 8760.0) -> float:
    """Combine fault severity (0..1) and normalized RUL into an index of 0..100."""
    sev_term = (1.0 - max(0.0, min(1.0, severity))) * 60.0
    rul_term = max(0.0, min(1.0, rul_hours / rul_reference_hours)) * 40.0
    return round(sev_term + rul_term, 1)
