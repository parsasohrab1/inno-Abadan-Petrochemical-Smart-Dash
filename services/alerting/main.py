"""API + alert worker — consumes events.alerts, stores, deduplicates, notifies, in-app replay."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import Session, select

from services.alerting.notifier import dispatch
from services.common.bus import EventBus, consume
from services.common.config import get_settings
from services.common.db import get_session, init_db, session_scope
from services.common.domain.enums import AlertSeverity, Role
from services.common.domain.models import Alert
from services.common.logging import get_logger
from services.common.security import TokenData, require_role
from services.common.service import create_app

log = get_logger("alerting")
_settings = get_settings()
_bus = EventBus("alerting")
DbSession = Annotated[Session, Depends(get_session)]

_DEDUP_WINDOW = timedelta(minutes=30)


async def _handle(topic: str, msg: dict) -> None:
    code = msg.get("code", "GENERIC")
    tag = msg.get("equipment_tag")
    device = msg.get("device_tag")
    now = datetime.now(timezone.utc)

    with session_scope() as s:
        recent = s.exec(
            select(Alert).where(
                Alert.code == code,
                Alert.equipment_tag == tag,
                Alert.device_tag == device,
                Alert.created_at >= now - _DEDUP_WINDOW,
                Alert.resolved_at.is_(None),
            )
        ).first()
        if recent:
            return
        alert = Alert(
            created_at=now,
            equipment_tag=tag,
            device_tag=device,
            severity=AlertSeverity(msg.get("severity", "warning")),
            code=code,
            title=msg.get("title", code),
            description=msg.get("description"),
            is_predictive=bool(msg.get("is_predictive")),
            predicted_failure_at=(
                datetime.fromisoformat(msg["predicted_failure_at"])
                if msg.get("predicted_failure_at") else None
            ),
        )
        s.add(alert)
        s.flush()
        alert_id = alert.id
        payload = {
            "id": alert_id, "code": code, "title": alert.title, "severity": alert.severity,
            "equipment_tag": tag, "device_tag": device, "is_predictive": alert.is_predictive,
            "description": alert.description, "created_at": now.isoformat(),
        }

    result = dispatch(payload["severity"], payload["title"], payload["description"] or "")
    await _bus.publish("events.alerts_inapp", {**payload, "channels": result}, key=tag or device or code)
    log.info("alert.raised", id=alert_id, code=code, severity=payload["severity"], channels=result)


async def _startup() -> None:
    init_db()
    await _bus.start()
    asyncio.create_task(consume([_settings.kafka_topic_alerts], "alerting", _handle))


app = create_app("alerting", on_startup=_startup)


@app.get("/alerts", tags=["alerts"])
def list_alerts(
    db: DbSession, active_only: bool = True, severity: str | None = None,
    equipment_tag: str | None = None, limit: int = 200,
) -> list[Alert]:
    q = select(Alert).order_by(Alert.created_at.desc())
    if active_only:
        q = q.where(Alert.resolved_at.is_(None))
    if severity:
        q = q.where(Alert.severity == severity)
    if equipment_tag:
        q = q.where(Alert.equipment_tag == equipment_tag)
    return db.exec(q.limit(limit)).all()


@app.get("/alerts/summary", tags=["alerts"])
def summary(db: DbSession) -> dict:
    rows = db.exec(select(Alert).where(Alert.resolved_at.is_(None))).all()
    by_sev: dict[str, int] = {}
    for r in rows:
        by_sev[r.severity] = by_sev.get(r.severity, 0) + 1
    return {"active_total": len(rows), "by_severity": by_sev,
            "predictive": sum(1 for r in rows if r.is_predictive)}


@app.post("/alerts/{alert_id}/ack", tags=["alerts"])
def acknowledge(
    alert_id: int, db: DbSession,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
) -> Alert:
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    a.acknowledged_by = user.sub
    a.acknowledged_at = datetime.now(timezone.utc)
    db.add(a)
    return a


@app.post("/alerts/{alert_id}/resolve", tags=["alerts"])
def resolve(
    alert_id: int, db: DbSession,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
) -> Alert:
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    a.resolved_at = datetime.now(timezone.utc)
    if not a.acknowledged_by:
        a.acknowledged_by = user.sub
        a.acknowledged_at = a.resolved_at
    db.add(a)
    return a
