"""Consume analytics.diagnosis → severity trend → RUL → update health index + predictive alert."""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlmodel import select

from ml.models.rul_estimator import RulEstimator
from services.common.bus import EventBus, consume
from services.common.config import get_settings
from services.common.db import init_db, session_scope
from services.common.domain.enums import FaultType
from services.common.domain.health import equipment_color, health_score_from
from services.common.domain.models import Equipment, RulEstimate
from services.common.logging import get_logger
from services.common.tsdb import tsdb

log = get_logger("prediction-rul")
_settings = get_settings()
_bus = EventBus("prediction-rul")
_rul = RulEstimator.load(_settings.model_registry_path)

_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=40))  # (t_seconds, severity)
_alerted: dict[str, datetime] = {}


def _trend_slope(points: deque) -> float:
    if len(points) < 4:
        return 0.0
    t = np.array([p[0] for p in points])
    s = np.array([p[1] for p in points])
    t = (t - t[0]) / 3600.0  # hours
    if t[-1] <= 0:
        return 0.0
    slope = np.polyfit(t, s, 1)[0]
    return float(max(0.0, slope))


async def _on_diagnosis(topic: str, msg: dict) -> None:
    tag = msg["equipment_tag"]
    severity = float(msg["severity"])
    now = datetime.now(timezone.utc)
    _history[tag].append((now.timestamp(), severity))
    slope = _trend_slope(_history[tag])

    with session_scope() as s:
        eq = s.exec(select(Equipment).where(Equipment.tag == tag)).first()
        life_scale = 0.5
        age_fraction = 0.4
        if eq and eq.install_year:
            age_years = max(0, now.year - eq.install_year)
            age_fraction = float(np.clip(age_years / 40.0, 0.02, 0.98))
            life_scale = float(np.clip(1.0 - age_fraction * 0.6, 0.15, 1.0))

        rul_hours, confidence = _rul.predict(severity, slope, age_fraction, life_scale)
        if msg["fault_type"] == FaultType.NORMAL.value:
            rul_hours = max(rul_hours, 20000.0)

        score = health_score_from(severity, rul_hours)
        failure_at = now + timedelta(hours=rul_hours)

        s.add(RulEstimate(
            equipment_tag=tag, ts=now, predicted_rul_hours=round(rul_hours, 1),
            confidence=round(confidence, 3), predicted_failure_at=failure_at, health_score=score,
        ))
        if eq:
            eq.health_score = score
            eq.health_color = equipment_color(score)
            s.add(eq)

    tsdb.write_reading("rul", {"equipment_tag": tag},
                       {"rul_hours": round(rul_hours, 1), "health_score": score, "trend_slope": slope})

    await _bus.publish(
        "analytics.rul",
        {"equipment_tag": tag, "ts": now.isoformat(), "predicted_rul_hours": round(rul_hours, 1),
         "confidence": round(confidence, 3), "predicted_failure_at": failure_at.isoformat(),
         "health_score": score},
        key=tag,
    )

    lead = _settings.rul_alert_lead_time_hours
    if rul_hours <= lead and msg["fault_type"] != FaultType.NORMAL.value:
        last = _alerted.get(tag)
        if not last or (now - last) > timedelta(hours=6):
            _alerted[tag] = now
            await _bus.publish(
                _settings.kafka_topic_alerts,
                {
                    "code": "PREDICTIVE_FAILURE",
                    "title": f"Imminent failure of {tag} — {msg['fault_type']}",
                    "severity": "critical" if rul_hours < lead / 2 else "major",
                    "equipment_tag": tag,
                    "ts": now.isoformat(),
                    "is_predictive": True,
                    "predicted_failure_at": failure_at.isoformat(),
                    "description": (
                        f"RUL ≈ {rul_hours:.0f} hours (confidence {confidence:.0%}); "
                        f"severity trend slope {slope:.4f}/h; health index {score}"
                    ),
                },
                key=tag,
            )
            log.info("rul.predictive_alert", equipment=tag, rul_hours=round(rul_hours), score=score)


async def main() -> None:
    init_db()
    await _bus.start()
    log.info("prediction-rul.model", estimator="trained" if _rul.estimator else "analytic-fallback")
    await consume([_settings.kafka_topic_diagnosis], "prediction-rul", _on_diagnosis)


if __name__ == "__main__":
    asyncio.run(main())
