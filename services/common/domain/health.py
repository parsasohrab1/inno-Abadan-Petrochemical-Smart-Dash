"""منطق پایش سلامت — سه‌چراغ سبز/زرد/قرمز برای سنسور، دوربین و تجهیز.

- سنسور/دوربین: بر پایه‌ی ۶ پارامتر README §۵-۲.
- تجهیز: بر پایه‌ی شاخص سلامت ۰..۱۰۰ (README §۴-۱).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.common.domain.enums import HealthColor


@dataclass
class DeviceHealthInputs:
    supply_voltage: float = 24.0          # V   (مجاز: ۲۴ ± ۵٪ سبز، ± ۱۰٪ زرد)
    loop_current_ma: float = 12.0         # mA  (مجاز: ۴..۲۰)
    snr_db: float = 40.0                  # dB
    calibration_drift_pct: float = 0.0    # ٪ انحراف از مرجع
    comm_latency_ms: float = 50.0         # ms
    comm_gap_s: float = 0.0               # ثانیه از آخرین داده
    device_temp_c: float = 40.0           # °C
    device_temp_limit_c: float = 85.0
    days_since_calibration: float = 10.0


@dataclass
class HealthResult:
    status: HealthColor
    reasons: list[str] = field(default_factory=list)


def evaluate_device_health(x: DeviceHealthInputs) -> HealthResult:
    """قانون پیش‌فرض؛ در `infra/postgres` یا فایل قواعد قابل override است."""
    red: list[str] = []
    yellow: list[str] = []

    # ۱ ولتاژ تغذیه
    dv = abs(x.supply_voltage - 24.0) / 24.0
    if dv > 0.10:
        red.append(f"ولتاژ تغذیه {x.supply_voltage:.1f}V خارج از ±۱۰٪")
    elif dv > 0.05:
        yellow.append(f"ولتاژ تغذیه {x.supply_voltage:.1f}V خارج از ±۵٪")

    # ۲ سیگنال خروجی 4-20mA
    if not (3.6 <= x.loop_current_ma <= 20.5):
        red.append(f"جریان حلقه {x.loop_current_ma:.1f}mA خارج از ۴..۲۰")
    elif not (4.0 <= x.loop_current_ma <= 20.0):
        yellow.append(f"جریان حلقه {x.loop_current_ma:.1f}mA در مرز اشباع")

    # ۳ کیفیت سیگنال (SNR)
    if x.snr_db < 12:
        red.append(f"SNR پایین {x.snr_db:.0f}dB")
    elif x.snr_db < 20:
        yellow.append(f"SNR ضعیف {x.snr_db:.0f}dB")

    # ۴ دقت اندازه‌گیری (انحراف کالیبراسیون)
    if x.calibration_drift_pct > 5:
        red.append(f"انحراف کالیبراسیون {x.calibration_drift_pct:.1f}٪")
    elif x.calibration_drift_pct > 2:
        yellow.append(f"انحراف کالیبراسیون {x.calibration_drift_pct:.1f}٪")

    # ۵ ارتباطات
    if x.comm_gap_s > 60:
        red.append(f"قطع ارتباط {x.comm_gap_s:.0f}s")
    elif x.comm_latency_ms > 500 or x.comm_gap_s > 10:
        yellow.append("تأخیر ارتباطی بالا")

    # ۶ دمای عملیاتی سنسور
    if x.device_temp_c > x.device_temp_limit_c:
        red.append(f"دمای سنسور {x.device_temp_c:.0f}°C فراتر از حد")
    elif x.device_temp_c > x.device_temp_limit_c - 10:
        yellow.append("دمای سنسور نزدیک حد مجاز")

    # کالیبراسیون منقضی
    if x.days_since_calibration > 180:
        red.append("کالیبراسیون بیش از ۱۸۰ روز")
    elif x.days_since_calibration > 90:
        yellow.append("کالیبراسیون بیش از ۹۰ روز")

    if red:
        return HealthResult(HealthColor.RED, red + yellow)
    if yellow:
        return HealthResult(HealthColor.YELLOW, yellow)
    return HealthResult(HealthColor.GREEN, ["عملکرد عادی"])


# آستانه‌های رنگ تجهیز بر اساس شاخص سلامت (قابل تنظیم)
EQUIPMENT_GREEN_MIN = 75.0
EQUIPMENT_YELLOW_MIN = 45.0


def equipment_color(health_score: float) -> HealthColor:
    if health_score >= EQUIPMENT_GREEN_MIN:
        return HealthColor.GREEN
    if health_score >= EQUIPMENT_YELLOW_MIN:
        return HealthColor.YELLOW
    return HealthColor.RED


def health_score_from(severity: float, rul_hours: float, rul_reference_hours: float = 8760.0) -> float:
    """ترکیب شدت عیب (۰..۱) و RUL نرمال‌شده به شاخص ۰..۱۰۰."""
    sev_term = (1.0 - max(0.0, min(1.0, severity))) * 60.0
    rul_term = max(0.0, min(1.0, rul_hours / rul_reference_hours)) * 40.0
    return round(sev_term + rul_term, 1)
