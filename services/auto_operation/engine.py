"""Auto Operation decision engine — README §6-2 (5 levels) and §6-3 (actions).

Flow: analytics.diagnosis + analytics.rul  →  evaluation  →  proposed/automatic action.
Online optimization: choosing between "continue with reduced load", "switch to standby" and "stop" based on
instantaneous cost-benefit analysis.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlmodel import select

from services.auto_operation import control
from services.common.bus import EventBus
from services.common.config import get_settings
from services.common.db import session_scope
from services.common.domain.enums import (
    ActionStatus,
    AutoActionType,
    AutoOpMode,
    Criticality,
    EquipmentRunState,
)
from services.common.domain.models import (
    AutoAction,
    Diagnosis,
    Equipment,
    MaintenanceRecord,
    RulEstimate,
)
from services.common.economics import (
    DEFAULT_PRICE_BOOK,
    avoided_catastrophic_value,
    avoided_downtime_value,
    load_price_book,
    planned_repair_saving,
)
from services.common.logging import get_logger

log = get_logger("auto-operation.engine")
_settings = get_settings()
_price_book = load_price_book()

# actions that, if configured globally, always require human approval (FR-17)
_HITL_ACTIONS = {
    AutoActionType.EQUIPMENT_STOP,
    AutoActionType.EQUIPMENT_START,
    AutoActionType.SPARE_CHANGEOVER,
    AutoActionType.LINE_SWITCH,
}


@dataclass
class RulState:
    rul_hours: float = 1e9
    confidence: float = 0.0
    health_score: float = 100.0
    updated: datetime | None = None


class DecisionEngine:
    def __init__(self) -> None:
        self.bus = EventBus("auto-operation-engine")
        self._rul: dict[str, RulState] = {}
        self._action_times: list[datetime] = []
        self.mode = AutoOpMode(_settings.auto_op_mode)

    async def start(self) -> None:
        await self.bus.start()

    # -------------------------------------------------- ingest
    def update_rul(self, tag: str, msg: dict) -> None:
        self._rul[tag] = RulState(
            rul_hours=float(msg["predicted_rul_hours"]),
            confidence=float(msg.get("confidence", 0)),
            health_score=float(msg.get("health_score", 100)),
            updated=datetime.now(timezone.utc),
        )

    async def on_diagnosis(self, msg: dict) -> None:
        tag = msg["equipment_tag"]
        fault = msg["fault_type"]
        severity = float(msg["severity"])
        if fault == "normal" and severity < 0.15:
            return
        rul = self._rul.get(tag, RulState())
        await self._evaluate(tag, fault, severity, rul)

    # -------------------------------------------------- core decision
    async def _evaluate(self, tag: str, fault: str, severity: float, rul: RulState) -> None:
        with session_scope() as s:
            eq = s.exec(select(Equipment).where(Equipment.tag == tag)).first()
            if not eq or eq.run_state in {EquipmentRunState.MAINTENANCE, EquipmentRunState.STOPPED}:
                return
            crit = Criticality(eq.criticality)
            has_spare = self._has_spare(s, eq)
            etype = eq.etype
            line_product = self._line_product(s, eq)
            rated_kw = eq.rated_power_kw or 75.0

            # do not create a repeated open action for the same equipment
            existing = s.exec(
                select(AutoAction).where(
                    AutoAction.equipment_tag == tag,
                    AutoAction.status.in_([ActionStatus.PROPOSED, ActionStatus.AWAITING_APPROVAL,
                                           ActionStatus.APPROVED, ActionStatus.EXECUTING]),
                )
            ).first()
            if existing:
                return

        lead = _settings.rul_alert_lead_time_hours
        actions: list[tuple[AutoActionType, int, str, dict, float]] = []

        # ---- Level 4: recommendation (load reduction / maintenance scheduling) ----
        if 0.25 <= severity < 0.55 and rul.rul_hours > lead:
            actions.append((
                AutoActionType.PARAMETER_ADJUSTMENT, 4,
                f"15% load reduction to contain the growth of fault '{fault}' (severity {severity:.2f})",
                {"parameter": "load_setpoint", "delta_pct": -15}, 0.0,
            ))
            actions.append((
                AutoActionType.MAINTENANCE_SCHEDULING, 4,
                f"Schedule planned maintenance within the RUL window ≈{rul.rul_hours:.0f}h",
                {"window_hours": rul.rul_hours}, planned_repair_saving(
                    _price_book["catastrophic_failure_cost_usd"].get(etype, 60000.0) * 0.3, _price_book),
            ))
            actions.append((
                AutoActionType.SPARE_PART_ORDER, 3,
                f"Order spare parts corresponding to fault '{fault}'",
                {"fault": fault}, 0.0,
            ))

        # ---- Level 5: action (standby changeover / stop) ----
        urgent = severity >= 0.6 or rul.rul_hours <= lead
        very_urgent = severity >= 0.8 or rul.rul_hours <= lead / 3

        if urgent:
            downtime_avoided = 8.0 if line_product else 3.0
            save_downtime = avoided_downtime_value(downtime_avoided, line_product or "default", _price_book)
            save_catastrophic = avoided_catastrophic_value(etype, 0.6 * severity, _price_book)
            total_save = round(save_downtime + save_catastrophic, 2)

            if has_spare:
                actions.append((
                    AutoActionType.SPARE_CHANGEOVER, 5,
                    (f"Automatic changeover to standby: start the standby and shut down {tag} "
                     f"(severity {severity:.2f}, RUL≈{rul.rul_hours:.0f}h). "
                     f"Estimated savings ${total_save:,.0f}."),
                    {"strategy": "start_spare_then_stop_main"}, total_save,
                ))
            elif crit in {Criticality.SAFETY_CRITICAL} and very_urgent:
                actions.append((
                    AutoActionType.EQUIPMENT_STOP, 5,
                    (f"Controlled stop of {tag} — safety-critical equipment without a standby, "
                     f"RUL≈{rul.rul_hours:.0f}h. Preventing a catastrophic failure."),
                    {"emergency": very_urgent and rul.rul_hours <= lead / 6}, save_catastrophic,
                ))
                actions.append((
                    AutoActionType.MAINTENANCE_REQUEST, 5,
                    "Urgent maintenance request after the stop", {"priority": "immediate"}, 0.0,
                ))
            else:
                actions.append((
                    AutoActionType.MAINTENANCE_REQUEST, 5,
                    (f"High-priority maintenance request for {tag} (no standby, "
                     f"load reduced as much as possible)."),
                    {"priority": "high"}, planned_repair_saving(save_catastrophic, _price_book),
                ))
                actions.append((
                    AutoActionType.PARAMETER_ADJUSTMENT, 4,
                    "30% load reduction until maintenance", {"parameter": "load_setpoint", "delta_pct": -30}, 0.0,
                ))

        for atype, level, rationale, params, savings in actions:
            await self._persist_and_maybe_execute(tag, atype, level, rationale, params, savings, crit, fault)

    # -------------------------------------------------- persistence + execution
    async def _persist_and_maybe_execute(
        self, tag: str, atype: AutoActionType, level: int, rationale: str,
        params: dict, savings: float, crit: Criticality, fault: str,
    ) -> None:
        requires_approval = self._requires_approval(atype, crit)
        now = datetime.now(timezone.utc)

        with session_scope() as s:
            action = AutoAction(
                created_at=now, action_type=atype, equipment_tag=tag, level=level,
                rationale=rationale, parameters_json=json.dumps(params, ensure_ascii=False),
                requires_human_approval=requires_approval, estimated_savings_usd=savings,
                status=ActionStatus.AWAITING_APPROVAL if requires_approval else ActionStatus.APPROVED,
            )
            s.add(action)
            s.flush()
            action_id = action.id

        await self._emit(action_id, atype, tag, ActionStatus.AWAITING_APPROVAL if requires_approval
                         else ActionStatus.APPROVED, level, rationale, savings)
        log.info("engine.action", id=action_id, type=atype.value, equipment=tag,
                 approval=requires_approval, savings=savings)

        if not requires_approval and self._within_rate_limit():
            await self.execute(action_id)

    def _requires_approval(self, atype: AutoActionType, crit: Criticality) -> bool:
        if self.mode == AutoOpMode.ADVISORY:
            return True
        if _settings.auto_op_require_human_approval and atype in _HITL_ACTIONS:
            return True
        if crit == Criticality.SAFETY_CRITICAL and atype in _HITL_ACTIONS:
            return True
        if self.mode == AutoOpMode.SUPERVISED and atype in _HITL_ACTIONS:
            return True
        return False

    def _within_rate_limit(self) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        self._action_times = [t for t in self._action_times if t > cutoff]
        if len(self._action_times) >= _settings.auto_op_max_autonomous_actions_per_hour:
            log.warning("engine.rate_limit.hit")
            return False
        return True

    async def execute(self, action_id: int) -> dict:
        with session_scope() as s:
            action = s.get(AutoAction, action_id)
            if not action or action.status not in {ActionStatus.APPROVED, ActionStatus.AWAITING_APPROVAL}:
                return {"error": "The action cannot be executed", "status": action.status if action else None}
            action.status = ActionStatus.EXECUTING
            s.add(action)
            atype = AutoActionType(action.action_type)
            tag = action.equipment_tag
            params = json.loads(action.parameters_json or "{}")
            savings = action.estimated_savings_usd

        result: dict = {}
        try:
            if atype == AutoActionType.SPARE_CHANGEOVER:
                result = await control.changeover_to_spare(tag, "auto-operation", action_id,
                                                           note="online optimization changeover")
                self._record_maintenance(tag, action_id, "planned repair after changeover", savings)
            elif atype == AutoActionType.EQUIPMENT_STOP:
                result = await control.stop_equipment(tag, "auto-operation", action_id,
                                                      emergency=bool(params.get("emergency")))
            elif atype == AutoActionType.EQUIPMENT_START:
                result = await control.start_equipment(tag, "auto-operation", action_id)
            elif atype == AutoActionType.PARAMETER_ADJUSTMENT:
                result = {"applied": params, "note": "setpoint writeback to DCS (stub)"}
            elif atype in {AutoActionType.MAINTENANCE_REQUEST, AutoActionType.MAINTENANCE_SCHEDULING}:
                result = {"work_order": f"WO-{action_id}", "params": params}
            elif atype == AutoActionType.SPARE_PART_ORDER:
                result = {"purchase_req": f"PR-{action_id}", "params": params}
            else:
                result = {"note": f"{atype.value} executed"}
            status = ActionStatus.SUCCESS
        except Exception as exc:  # noqa: BLE001
            log.exception("engine.execute.failed", action_id=action_id)
            result = {"error": str(exc)}
            status = ActionStatus.FAILED

        self._action_times.append(datetime.now(timezone.utc))
        with session_scope() as s:
            action = s.get(AutoAction, action_id)
            action.status = status
            action.executed_at = datetime.now(timezone.utc)
            action.result_json = json.dumps(result, ensure_ascii=False, default=str)
            s.add(action)

        await self._emit(action_id, atype, tag, status, None, None,
                         savings if status == ActionStatus.SUCCESS else 0.0)
        return {"action_id": action_id, "status": status, "result": result}

    def _record_maintenance(self, tag: str, action_id: int, note: str, savings: float) -> None:
        with session_scope() as s:
            eq = s.exec(select(Equipment).where(Equipment.tag == tag)).first()
            if eq:
                s.add(MaintenanceRecord(
                    equipment_id=eq.id, performed_at=datetime.now(timezone.utc),
                    action=note, source_action_id=action_id, cost_usd=0.0, downtime_hours=0.0,
                ))

    async def _emit(self, action_id, atype, tag, status, level, rationale, savings) -> None:
        await self.bus.publish(
            _settings.kafka_topic_auto_ops,
            {
                "action_id": action_id, "action_type": atype.value if hasattr(atype, "value") else atype,
                "equipment_tag": tag, "status": status.value if hasattr(status, "value") else status,
                "level": level or 0, "rationale": rationale, "estimated_savings_usd": savings,
                "ts": datetime.now(timezone.utc).isoformat(),
            },
            key=tag,
        )

    # -------------------------------------------------- helpers
    @staticmethod
    def _has_spare(session, eq: Equipment) -> bool:
        spare = session.exec(select(Equipment).where(Equipment.spare_of_id == eq.id)).first()
        return spare is not None and spare.run_state in {
            EquipmentRunState.STANDBY, EquipmentRunState.STOPPED
        }

    @staticmethod
    def _line_product(session, eq: Equipment) -> str | None:
        from services.common.domain.models import ProductionLine

        line = session.get(ProductionLine, eq.line_id)
        return line.product if line else None
