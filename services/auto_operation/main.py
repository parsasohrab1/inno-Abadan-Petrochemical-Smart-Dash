"""Auto Operation API + background worker."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from services.auto_operation import control
from services.auto_operation.engine import DecisionEngine
from services.common.bus import consume
from services.common.config import get_settings
from services.common.db import get_session, init_db
from services.common.domain.enums import ActionStatus, AutoOpMode, Role
from services.common.domain.models import AutoAction
from services.common.logging import get_logger
from services.common.security import TokenData, require_role
from services.common.service import create_app

log = get_logger("auto-operation")
_settings = get_settings()
_engine = DecisionEngine()
DbSession = Annotated[Session, Depends(get_session)]


async def _consumer() -> None:
    async def handle(topic: str, msg: dict) -> None:
        if topic == _settings.kafka_topic_diagnosis:
            await _engine.on_diagnosis(msg)
        elif topic == "analytics.rul":
            _engine.update_rul(msg["equipment_tag"], msg)

    await consume([_settings.kafka_topic_diagnosis, "analytics.rul"], "auto-operation", handle)


async def _startup() -> None:
    init_db()
    await _engine.start()
    asyncio.create_task(_consumer())
    log.info("auto-operation.ready", mode=_engine.mode.value)


app = create_app("auto-operation", on_startup=_startup)


# ------------------------------------------------------------------ actions
@app.get("/actions", tags=["actions"])
def list_actions(db: DbSession, status: str | None = None, equipment_tag: str | None = None,
                 limit: int = 100) -> list[AutoAction]:
    q = select(AutoAction).order_by(AutoAction.created_at.desc())
    if status:
        q = q.where(AutoAction.status == status)
    if equipment_tag:
        q = q.where(AutoAction.equipment_tag == equipment_tag)
    return db.exec(q.limit(limit)).all()


@app.get("/actions/pending", tags=["actions"])
def pending_actions(db: DbSession) -> list[AutoAction]:
    return db.exec(
        select(AutoAction)
        .where(AutoAction.status == ActionStatus.AWAITING_APPROVAL)
        .order_by(AutoAction.level.desc(), AutoAction.created_at.desc())
    ).all()


@app.get("/actions/{action_id}", tags=["actions"])
def get_action(action_id: int, db: DbSession) -> AutoAction:
    a = db.get(AutoAction, action_id)
    if not a:
        raise HTTPException(404, "Action not found")
    return a


@app.post("/actions/{action_id}/approve", tags=["actions"])
async def approve_action(
    action_id: int, db: DbSession,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
) -> dict:
    a = db.get(AutoAction, action_id)
    if not a or a.status != ActionStatus.AWAITING_APPROVAL:
        raise HTTPException(400, "The action is not pending approval")
    a.status = ActionStatus.APPROVED
    a.approved_by = user.sub
    a.decided_at = datetime.now(timezone.utc)
    db.add(a)
    db.commit()
    return await _engine.execute(action_id)


@app.post("/actions/{action_id}/reject", tags=["actions"])
def reject_action(
    action_id: int, db: DbSession,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
    reason: str = "",
) -> AutoAction:
    a = db.get(AutoAction, action_id)
    if not a or a.status != ActionStatus.AWAITING_APPROVAL:
        raise HTTPException(400, "The action is not pending approval")
    a.status = ActionStatus.REJECTED
    a.approved_by = user.sub
    a.decided_at = datetime.now(timezone.utc)
    a.result_json = f'{{"rejected_reason": "{reason}"}}'
    db.add(a)
    return a


# ------------------------------------------------------------------ manual control
class ControlBody(BaseModel):
    note: str | None = None
    emergency: bool = False


@app.get("/equipment/{tag}/state", tags=["control"])
def get_state(tag: str) -> dict:
    try:
        return control.equipment_state(tag)
    except control.ControlError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/control/{tag}/start", tags=["control"])
async def manual_start(
    tag: str, body: ControlBody,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
) -> dict:
    try:
        return await control.start_equipment(tag, f"operator:{user.sub}", note=body.note)
    except control.ControlError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/control/{tag}/stop", tags=["control"])
async def manual_stop(
    tag: str, body: ControlBody,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
) -> dict:
    try:
        return await control.stop_equipment(tag, f"operator:{user.sub}", note=body.note,
                                            emergency=body.emergency)
    except control.ControlError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/control/{tag}/changeover", tags=["control"])
async def manual_changeover(
    tag: str, body: ControlBody,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
) -> dict:
    try:
        return await control.changeover_to_spare(tag, f"operator:{user.sub}", note=body.note)
    except control.ControlError as exc:
        raise HTTPException(400, str(exc)) from exc


# ------------------------------------------------------------------ policy
class PolicyBody(BaseModel):
    mode: AutoOpMode


@app.get("/policy", tags=["policy"])
def get_policy() -> dict:
    return {
        "mode": _engine.mode.value,
        "require_human_approval": _settings.auto_op_require_human_approval,
        "max_autonomous_actions_per_hour": _settings.auto_op_max_autonomous_actions_per_hour,
        "rul_alert_lead_time_hours": _settings.rul_alert_lead_time_hours,
    }


@app.patch("/policy", tags=["policy"])
def set_policy(
    body: PolicyBody,
    user: Annotated[TokenData, Depends(require_role(Role.ENGINEER))],
) -> dict:
    _engine.mode = body.mode
    log.info("auto-operation.policy.changed", mode=body.mode.value, by=user.sub)
    return {"mode": _engine.mode.value}


@app.get("/stats", tags=["meta"])
def stats(db: DbSession) -> dict:
    rows = db.exec(select(AutoAction)).all()
    by_status: dict[str, int] = {}
    total_savings = 0.0
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        if r.status == ActionStatus.SUCCESS:
            total_savings += r.estimated_savings_usd
    return {
        "mode": _engine.mode.value,
        "total_actions": len(rows),
        "by_status": by_status,
        "realized_savings_usd": round(total_savings, 2),
    }
