"""Logic for building reports from the database and other services."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlmodel import select

from services.common.db import session_scope
from services.common.domain.enums import ActionStatus, HealthColor
from services.common.domain.models import (
    Alert,
    AutoAction,
    Diagnosis,
    EconomicsSnapshot,
    Equipment,
    MaintenanceRecord,
    Report,
    RulEstimate,
    Sensor,
)


def _period(kind: str) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    delta = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1),
             "monthly": timedelta(days=30), "cost_benefit": timedelta(days=30),
             "ai_performance": timedelta(days=7)}.get(kind, timedelta(days=1))
    return end - delta, end


def generate(kind: str) -> Report:
    start, end = _period(kind)
    with session_scope() as s:
        if kind in {"daily", "weekly", "monthly"}:
            payload, summary, title = _operational(s, kind, start, end)
        elif kind == "cost_benefit":
            payload, summary, title = _cost_benefit(s, start, end)
        elif kind == "ai_performance":
            payload, summary, title = _ai_performance(s, start, end)
        else:
            raise ValueError(f"Unknown report type: {kind}")

        report = Report(
            kind=kind, period_start=start, period_end=end, title=title,
            summary=summary, payload_json=json.dumps(payload, ensure_ascii=False, default=str),
        )
        s.add(report)
        s.flush()
        s.refresh(report)
        return report


def _operational(s, kind: str, start: datetime, end: datetime):
    equipment = s.exec(select(Equipment)).all()
    by_color: dict[str, int] = {c.value: 0 for c in HealthColor}
    for e in equipment:
        by_color[e.health_color] = by_color.get(e.health_color, 0) + 1

    alerts = s.exec(select(Alert).where(Alert.created_at >= start)).all()
    actions = s.exec(select(AutoAction).where(AutoAction.created_at >= start)).all()
    diags = s.exec(
        select(Diagnosis.fault_type, func.count())
        .where(Diagnosis.ts >= start, Diagnosis.severity >= 0.3)
        .group_by(Diagnosis.fault_type)
    ).all()
    worst = s.exec(
        select(Equipment).order_by(Equipment.health_score.asc()).limit(10)
    ).all()

    payload = {
        "equipment_health": by_color,
        "alerts": {
            "total": len(alerts),
            "critical": sum(1 for a in alerts if a.severity == "critical"),
            "predictive": sum(1 for a in alerts if a.is_predictive),
        },
        "auto_operation": {
            "total": len(actions),
            "executed": sum(1 for a in actions if a.status == ActionStatus.SUCCESS),
            "awaiting_approval": sum(1 for a in actions if a.status == ActionStatus.AWAITING_APPROVAL),
            "estimated_savings_usd": round(sum(a.estimated_savings_usd for a in actions
                                               if a.status == ActionStatus.SUCCESS), 2),
        },
        "top_faults": {ft: n for ft, n in diags},
        "watchlist": [
            {"tag": e.tag, "name": e.name, "health_score": e.health_score, "color": e.health_color,
             "run_state": e.run_state}
            for e in worst
        ],
        "recommendations": _recommendations(worst),
    }
    label = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}[kind]
    summary = (
        f"{label} report: {by_color.get('red', 0)} red equipment, "
        f"{payload['alerts']['total']} alerts, "
        f"{payload['auto_operation']['executed']} automatic actions executed, "
        f"estimated savings ${payload['auto_operation']['estimated_savings_usd']:,.0f}"
    )
    return payload, summary, f"{label} CBM status report"


def _cost_benefit(s, start: datetime, end: datetime):
    snaps = s.exec(
        select(EconomicsSnapshot).where(EconomicsSnapshot.ts >= start).order_by(EconomicsSnapshot.ts)
    ).all()
    maint = s.exec(select(MaintenanceRecord).where(MaintenanceRecord.performed_at >= start)).all()
    actions = s.exec(
        select(AutoAction).where(AutoAction.created_at >= start,
                                 AutoAction.status == ActionStatus.SUCCESS)
    ).all()

    total_savings = round(sum(a.estimated_savings_usd for a in actions), 2)
    maint_cost = round(sum(m.cost_usd for m in maint), 2)
    downtime_hours = round(sum(m.downtime_hours for m in maint), 1)
    avg_profit_rate = round(
        sum(x.profit_rate_usd_per_hour for x in snaps) / len(snaps), 2
    ) if snaps else 0.0

    # assumption of the capital and annual operating cost of the CBM system
    annual_capex_amortized = 1_800_000.0
    annual_opex = 600_000.0
    period_cost = (annual_capex_amortized + annual_opex) * ((end - start).days / 365.0)
    roi = round((total_savings - period_cost) / period_cost * 100, 1) if period_cost else None

    payload = {
        "period_days": (end - start).days,
        "estimated_savings_usd": total_savings,
        "maintenance_cost_usd": maint_cost,
        "unplanned_downtime_hours": downtime_hours,
        "avg_profit_rate_usd_per_hour": avg_profit_rate,
        "cbm_system_cost_for_period_usd": round(period_cost, 2),
        "roi_pct": roi,
        "actions_by_type": _count_by(actions, "action_type"),
    }
    summary = (
        f"Period savings ${total_savings:,.0f} versus the system cost "
        f"${period_cost:,.0f} — ROI ≈ {roi}%"
    )
    return payload, summary, "CBM system cost-benefit report"


def _ai_performance(s, start: datetime, end: datetime):
    diags = s.exec(select(Diagnosis).where(Diagnosis.ts >= start)).all()
    ruls = s.exec(select(RulEstimate).where(RulEstimate.ts >= start)).all()
    alerts = s.exec(select(Alert).where(Alert.created_at >= start)).all()
    sensors = s.exec(select(Sensor)).all()

    avg_conf = round(sum(d.confidence for d in diags) / len(diags), 3) if diags else 0.0
    predictive_alerts = [a for a in alerts if a.is_predictive]
    sensor_red = sum(1 for x in sensors if x.health_status == HealthColor.RED)

    payload = {
        "diagnoses": len(diags),
        "avg_confidence": avg_conf,
        "rul_estimates": len(ruls),
        "avg_rul_confidence": round(sum(r.confidence for r in ruls) / len(ruls), 3) if ruls else 0.0,
        "predictive_alerts": len(predictive_alerts),
        "false_alarm_rate_pct": _false_alarm_rate(s, start),
        "sensor_health": {
            "total": len(sensors),
            "red": sensor_red,
            "yellow": sum(1 for x in sensors if x.health_status == HealthColor.YELLOW),
        },
    }
    summary = (
        f"Mean diagnosis confidence {avg_conf:.0%}, {len(predictive_alerts)} predictive alerts, "
        f"false alarm rate {payload['false_alarm_rate_pct']}% (target < 5%)"
    )
    return payload, summary, "AI performance report"


def _false_alarm_rate(s, start: datetime) -> float:
    alerts = s.exec(select(Alert).where(Alert.created_at >= start, Alert.is_predictive.is_(True))).all()
    if not alerts:
        return 0.0
    # alerts that were resolved without any corresponding MaintenanceRecord ⇒ false-alarm candidates
    false_like = sum(1 for a in alerts if a.resolved_at and not a.acknowledged_by)
    return round(false_like / len(alerts) * 100, 1)


def _recommendations(worst: list[Equipment]) -> list[str]:
    out = []
    for e in worst:
        if e.health_score < 45:
            out.append(f"{e.tag}: urgent repair/replacement planning (index {e.health_score})")
        elif e.health_score < 75:
            out.append(f"{e.tag}: increase monitoring and inspection frequency (index {e.health_score})")
    return out


def _count_by(items, attr: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        k = getattr(it, attr)
        out[k] = out.get(k, 0) + 1
    return out
