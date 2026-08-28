"""مدل اقتصادی — محاسبه‌ی لحظه‌ای «سود ($)» و «صرفه‌جویی ($)» برای داشبرد مدیریتی.

الزام کاربر: «هر لحظه میزان سود به دلار و میزان صرفه‌جویی به دلار در داشبرد
برای مدیر نمایش داده شود».

منابع داده:
- نرخ تولید لحظه‌ای: فلومترهای خط تولید (telemetry.process → InfluxDB)
- قیمت محصول/خوراک/انرژی: price book (قابل ویرایش در `config/economics.yaml`)
- صرفه‌جویی CBM: مجموع اثر اقدامات Auto Operation + خرابی‌های پیش‌گیری‌شده
  (RUL alert که منجر به تعمیر برنامه‌ریزی‌شده شد) نسبت به سناریوی «بدون CBM».
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# ------------------------------------------------------------------ price book
DEFAULT_PRICE_BOOK: dict = {
    "currency": "USD",
    "products": {  # $/ton
        "PVC": 950.0,
        "Caustic": 450.0,
        "DDB": 1400.0,
        "Tetramer": 1600.0,
        "EDC": 350.0,
        "VCM": 800.0,
    },
    "feedstock_cost_per_ton_product": {  # $/ton محصول
        "PVC": 520.0,
        "Caustic": 120.0,
        "DDB": 700.0,
        "Tetramer": 780.0,
        "EDC": 180.0,
        "VCM": 430.0,
    },
    "energy": {
        "electricity_usd_per_kwh": 0.09,
        "steam_usd_per_ton": 22.0,
    },
    "downtime_cost_usd_per_hour": {  # هزینه‌ی توقف غیربرنامه‌ریزی‌شده هر خط
        "default": 12000.0,
        "PVC": 18000.0,
        "Caustic": 9000.0,
        "DDB": 7000.0,
    },
    # هزینه‌ی خرابی فاجعه‌بار (تعویض کامل + خسارت جانبی) بر اساس بحرانی‌بودن تجهیز
    "catastrophic_failure_cost_usd": {
        "pump": 45000.0,
        "compressor": 380000.0,
        "fan": 30000.0,
        "turbine": 550000.0,
        "motor": 40000.0,
        "default": 60000.0,
    },
    # نرخ پایه‌ی خرابی غیرمنتظره بدون CBM (رخداد در سال به ازای هر تجهیز بحرانی)
    "baseline_unplanned_failures_per_year_per_critical_equipment": 0.9,
    # نسبت خرابی‌هایی که CBM می‌تواند زودتر تشخیص دهد و به تعمیر برنامه‌ریزی‌شده تبدیل کند
    "cbm_preventable_fraction": 0.75,
    # کاهش هزینه‌ی هر تعمیر وقتی برنامه‌ریزی‌شده باشد (نسبت به اضطراری)
    "planned_vs_unplanned_repair_saving_fraction": 0.6,
}


def load_price_book(path: str | Path = "config/economics.yaml") -> dict:
    p = Path(path)
    if p.exists():
        loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        merged = {**DEFAULT_PRICE_BOOK, **loaded}
        for k, v in DEFAULT_PRICE_BOOK.items():
            if isinstance(v, dict):
                merged[k] = {**v, **loaded.get(k, {})}
        return merged
    return DEFAULT_PRICE_BOOK


# ------------------------------------------------------------------ profit
@dataclass
class LineProduction:
    line_code: str
    product: str
    rate_tph: float              # نرخ تولید لحظه‌ای (تن بر ساعت) از فلومتر
    power_kw: float = 0.0        # توان مصرفی لحظه‌ای خط
    steam_tph: float = 0.0


@dataclass
class ProfitResult:
    profit_rate_usd_per_hour: float
    revenue_rate_usd_per_hour: float
    cost_rate_usd_per_hour: float
    per_line: dict[str, float] = field(default_factory=dict)


def compute_profit_rate(lines: list[LineProduction], price_book: dict | None = None) -> ProfitResult:
    pb = price_book or DEFAULT_PRICE_BOOK
    revenue = 0.0
    cost = 0.0
    per_line: dict[str, float] = {}
    for ln in lines:
        price = pb["products"].get(ln.product, 0.0)
        feed = pb["feedstock_cost_per_ton_product"].get(ln.product, 0.0)
        line_rev = ln.rate_tph * price
        line_cost = (
            ln.rate_tph * feed
            + ln.power_kw * pb["energy"]["electricity_usd_per_kwh"]
            + ln.steam_tph * pb["energy"]["steam_usd_per_ton"]
        )
        revenue += line_rev
        cost += line_cost
        per_line[ln.line_code] = round(line_rev - line_cost, 2)
    return ProfitResult(
        profit_rate_usd_per_hour=round(revenue - cost, 2),
        revenue_rate_usd_per_hour=round(revenue, 2),
        cost_rate_usd_per_hour=round(cost, 2),
        per_line=per_line,
    )


# ------------------------------------------------------------------ savings (CBM value)
@dataclass
class SavingsBreakdown:
    avoided_downtime_usd: float = 0.0
    avoided_catastrophic_usd: float = 0.0
    planned_repair_saving_usd: float = 0.0
    energy_optimization_usd: float = 0.0
    total_usd: float = 0.0


def avoided_downtime_value(
    downtime_hours_avoided: float, line_product: str, price_book: dict | None = None
) -> float:
    pb = price_book or DEFAULT_PRICE_BOOK
    dc = pb["downtime_cost_usd_per_hour"]
    rate = dc.get(line_product, dc["default"])
    return round(downtime_hours_avoided * rate, 2)


def avoided_catastrophic_value(
    equipment_type: str, probability_reduced: float, price_book: dict | None = None
) -> float:
    pb = price_book or DEFAULT_PRICE_BOOK
    cc = pb["catastrophic_failure_cost_usd"]
    cost = cc.get(equipment_type, cc["default"])
    return round(cost * max(0.0, min(1.0, probability_reduced)), 2)


def planned_repair_saving(unplanned_repair_cost_usd: float, price_book: dict | None = None) -> float:
    pb = price_book or DEFAULT_PRICE_BOOK
    return round(
        unplanned_repair_cost_usd * pb["planned_vs_unplanned_repair_saving_fraction"], 2
    )


def annualized_baseline_saving(
    n_critical_equipment: int, price_book: dict | None = None
) -> float:
    """پتانسیل صرفه‌جویی سالانه‌ی مرجع (برای مقایسه‌ی روند)."""
    pb = price_book or DEFAULT_PRICE_BOOK
    failures = (
        n_critical_equipment
        * pb["baseline_unplanned_failures_per_year_per_critical_equipment"]
        * pb["cbm_preventable_fraction"]
    )
    avg_event_cost = pb["catastrophic_failure_cost_usd"]["default"] + pb[
        "downtime_cost_usd_per_hour"
    ]["default"] * 24
    return round(failures * avg_event_cost, 2)
