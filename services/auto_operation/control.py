"""Equipment on/off state machine + standby changeover.

In a real environment, `_send_command` connects to the DCS/PLC (OPC-UA writeback) or SIS.
Here the state is updated in the asset-registry database and an event is published.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import select

from services.common.bus import EventBus
from services.common.config import get_settings
from services.common.db import session_scope
from services.common.domain.enums import EquipmentRunState
from services.common.domain.models import Equipment, EquipmentStateChange
from services.common.logging import get_logger

log = get_logger("auto-operation.control")
_settings = get_settings()

# allowed state machine transitions
_ALLOWED: dict[EquipmentRunState, set[EquipmentRunState]] = {
    EquipmentRunState.RUNNING: {EquipmentRunState.STOPPING, EquipmentRunState.TRIPPED},
    EquipmentRunState.STOPPING: {EquipmentRunState.STOPPED, EquipmentRunState.TRIPPED},
    EquipmentRunState.STOPPED: {EquipmentRunState.STARTING, EquipmentRunState.MAINTENANCE, EquipmentRunState.STANDBY},
    EquipmentRunState.STANDBY: {EquipmentRunState.STARTING, EquipmentRunState.MAINTENANCE},
    EquipmentRunState.STARTING: {EquipmentRunState.RUNNING, EquipmentRunState.TRIPPED},
    EquipmentRunState.TRIPPED: {EquipmentRunState.STOPPED, EquipmentRunState.MAINTENANCE},
    EquipmentRunState.MAINTENANCE: {EquipmentRunState.STOPPED, EquipmentRunState.STANDBY},
}


class ControlError(RuntimeError):
    pass


async def _send_command(tag: str, command: str) -> None:
    """Connection point to the DCS/PLC. TODO: implement OPC-UA writeback with feedback confirmation."""
    log.info("control.command.dispatch", equipment=tag, command=command)


def _transition(session, tag: str, target: EquipmentRunState, triggered_by: str,
                action_id: int | None, note: str | None) -> Equipment:
    eq = session.exec(select(Equipment).where(Equipment.tag == tag)).first()
    if not eq:
        raise ControlError(f"Equipment {tag} not found")
    current = EquipmentRunState(eq.run_state)
    if target not in _ALLOWED.get(current, set()) and current != target:
        raise ControlError(f"Invalid transition {current.value} → {target.value} for {tag}")
    session.add(EquipmentStateChange(
        ts=datetime.now(timezone.utc), equipment_tag=tag, from_state=current,
        to_state=target, triggered_by=triggered_by, action_id=action_id, note=note,
    ))
    eq.run_state = target
    session.add(eq)
    return eq


async def start_equipment(tag: str, triggered_by: str, action_id: int | None = None,
                          note: str | None = None) -> dict:
    with session_scope() as s:
        _transition(s, tag, EquipmentRunState.STARTING, triggered_by, action_id, note)
    await _send_command(tag, "START")
    with session_scope() as s:
        eq = _transition(s, tag, EquipmentRunState.RUNNING, triggered_by, action_id, "start confirmed")
        result = {"tag": tag, "state": eq.run_state}
    log.info("control.started", equipment=tag, by=triggered_by)
    return result


async def stop_equipment(tag: str, triggered_by: str, action_id: int | None = None,
                         note: str | None = None, emergency: bool = False) -> dict:
    if emergency:
        with session_scope() as s:
            eq = _transition(s, tag, EquipmentRunState.TRIPPED, triggered_by, action_id, note or "ESD")
        await _send_command(tag, "TRIP")
    else:
        with session_scope() as s:
            _transition(s, tag, EquipmentRunState.STOPPING, triggered_by, action_id, note)
        await _send_command(tag, "STOP")
        with session_scope() as s:
            eq = _transition(s, tag, EquipmentRunState.STOPPED, triggered_by, action_id, "stop confirmed")
    log.info("control.stopped", equipment=tag, by=triggered_by, emergency=emergency)
    return {"tag": tag, "state": eq.run_state}


async def changeover_to_spare(main_tag: str, triggered_by: str, action_id: int | None = None,
                              note: str | None = None) -> dict:
    """Start the standby, then shut down the main equipment — without interrupting production."""
    with session_scope() as s:
        main_eq = s.exec(select(Equipment).where(Equipment.tag == main_tag)).first()
        if not main_eq:
            raise ControlError(f"Equipment {main_tag} not found")
        spare = s.exec(select(Equipment).where(Equipment.spare_of_id == main_eq.id)).first()
        if not spare:
            raise ControlError(f"No standby is defined for {main_tag}")
        spare_tag = spare.tag

    # 1) start the standby
    await start_equipment(spare_tag, triggered_by, action_id, note=f"changeover from {main_tag}")
    # 2) stop the main equipment and move it to maintenance
    await stop_equipment(main_tag, triggered_by, action_id, note=f"changeover to {spare_tag}")
    with session_scope() as s:
        _transition(s, main_tag, EquipmentRunState.MAINTENANCE, triggered_by, action_id,
                    "awaiting planned maintenance")

    bus = EventBus("auto-operation-control")
    await bus.start()
    await bus.publish(
        _settings.kafka_topic_auto_ops,
        {"action_type": "spare_changeover", "equipment_tag": main_tag, "target_tag": spare_tag,
         "status": "success", "ts": datetime.now(timezone.utc).isoformat(),
         "rationale": note or "auto changeover"},
        key=main_tag,
    )
    await bus.stop()
    log.info("control.changeover", main=main_tag, spare=spare_tag, by=triggered_by)
    return {"stopped": main_tag, "started": spare_tag}


def equipment_state(tag: str) -> dict:
    with session_scope() as s:
        eq = s.exec(select(Equipment).where(Equipment.tag == tag)).first()
        if not eq:
            raise ControlError(f"Equipment {tag} not found")
        history = s.exec(
            select(EquipmentStateChange)
            .where(EquipmentStateChange.equipment_tag == tag)
            .order_by(EquipmentStateChange.ts.desc())
            .limit(20)
        ).all()
        return {
            "tag": tag,
            "run_state": eq.run_state,
            "has_spare": eq.has_spare,
            "health_score": eq.health_score,
            "history": [h.model_dump() for h in history],
        }
