"""دروازه‌ی API — نقطه‌ی ورود واحد داشبرد (FR-18، FR-20)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy import func
from sqlmodel import Session, select

from services.api_gateway.auth import ensure_seed_users, router as auth_router
from services.api_gateway.live import router as live_router, start_pumps
from services.common.clients import auto_operation, economics, reporting
from services.common.db import get_session, init_db, session_scope
from services.common.domain.enums import HealthColor, Role
from services.common.domain.models import (
    Alert,
    AutoAction,
    Diagnosis,
    Equipment,
    ProductionLine,
    RulEstimate,
    Sensor,
    Camera,
    Unit,
)
from services.common.logging import get_logger
from services.common.security import TokenData, require_role
from services.common.service import create_app
from services.common.tsdb import tsdb

log = get_logger("api-gateway")
DbSession = Annotated[Session, Depends(get_session)]


async def _startup() -> None:
    init_db()
    with session_scope() as s:
        ensure_seed_users(s)
    start_pumps()


app = create_app("api-gateway", on_startup=_startup)
app.include_router(auth_router)
app.include_router(live_router)


# ------------------------------------------------------------------ overview (FR-18)
@app.get("/api/overview", tags=["dashboard"])
def overview(db: DbSession, user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]) -> dict:
    equipment = db.exec(select(Equipment)).all()
    sensors = db.exec(select(Sensor)).all()
    cameras = db.exec(select(Camera)).all()
    units = db.exec(select(Unit)).all()

    def color_counts(items, attr):
        c = {x.value: 0 for x in HealthColor}
        for it in items:
            c[getattr(it, attr)] = c.get(getattr(it, attr), 0) + 1
        return c

    active_alerts = db.exec(select(Alert).where(Alert.resolved_at.is_(None))).all()
    return {
        "equipment": {
            "total": len(equipment),
            "by_color": color_counts(equipment, "health_color"),
            "running": sum(1 for e in equipment if e.run_state == "running"),
            "standby": sum(1 for e in equipment if e.run_state == "standby"),
            "stopped": sum(1 for e in equipment if e.run_state in {"stopped", "tripped", "maintenance"}),
        },
        "sensors": {"total": len(sensors), "by_color": color_counts(sensors, "health_status")},
        "cameras": {"total": len(cameras), "by_color": color_counts(cameras, "health_status")},
        "alerts": {
            "active": len(active_alerts),
            "critical": sum(1 for a in active_alerts if a.severity == "critical"),
            "predictive": sum(1 for a in active_alerts if a.is_predictive),
        },
        "units": [
            {"code": u.code, "title": u.title, "criticality": u.criticality} for u in units
        ],
    }


@app.get("/api/heatmap", tags=["dashboard"])
def heatmap(db: DbSession, user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]) -> list[dict]:
    """نقشه‌ی حرارتی: هر تجهیز با رنگ سلامت و مختصات سلسله‌مراتبی."""
    rows = db.exec(
        select(Equipment, ProductionLine, Unit)
        .join(ProductionLine, Equipment.line_id == ProductionLine.id)
        .join(Unit, ProductionLine.unit_id == Unit.id)
    ).all()
    return [
        {
            "tag": e.tag, "name": e.name, "type": e.etype,
            "unit": u.code, "line": pl.code,
            "health_score": e.health_score, "color": e.health_color,
            "run_state": e.run_state, "criticality": e.criticality, "has_spare": e.has_spare,
        }
        for e, pl, u in rows
    ]


# ------------------------------------------------------------------ equipment detail
@app.get("/api/equipment/{tag}", tags=["dashboard"])
async def equipment_detail(
    tag: str, db: DbSession, user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]
) -> dict:
    eq = db.exec(select(Equipment).where(Equipment.tag == tag)).first()
    if not eq:
        from fastapi import HTTPException
        raise HTTPException(404, "تجهیز یافت نشد")

    last_diag = db.exec(
        select(Diagnosis).where(Diagnosis.equipment_tag == tag).order_by(Diagnosis.ts.desc())
    ).first()
    last_rul = db.exec(
        select(RulEstimate).where(RulEstimate.equipment_tag == tag).order_by(RulEstimate.ts.desc())
    ).first()
    alerts = db.exec(
        select(Alert).where(Alert.equipment_tag == tag, Alert.resolved_at.is_(None))
    ).all()

    state = {}
    try:
        ao = auto_operation()
        state = await ao.get(f"/equipment/{tag}/state")
        await ao.aclose()
    except Exception:  # noqa: BLE001
        pass

    return {
        "equipment": eq,
        "diagnosis": last_diag,
        "rul": last_rul,
        "alerts": alerts,
        "control_state": state,
        "trends": {
            "rms": tsdb.query_series("vibration_features", tag, "rms", timedelta(days=7)),
            "kurtosis": tsdb.query_series("vibration_features", tag, "kurtosis", timedelta(days=7)),
            "health_score": tsdb.query_series("rul", tag, "health_score", timedelta(days=30)),
            "rul_hours": tsdb.query_series("rul", tag, "rul_hours", timedelta(days=30)),
        },
    }


@app.get("/api/equipment/{tag}/spectrum", tags=["dashboard"])
def equipment_spectrum(tag: str, user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]) -> dict:
    """آخرین دامنه در مضارب فرکانس چرخش برای نمودار FFT/Waterfall."""
    orders = ["ord_0.5x", "ord_1x", "ord_2x", "ord_3x", "ord_4x", "ord_5x"]
    return {
        "orders": {
            o: tsdb.query_series("vibration_features", tag, o, timedelta(hours=6), every="30m")
            for o in orders
        }
    }


# ------------------------------------------------------------------ alerts / prediction
@app.get("/api/alerts", tags=["dashboard"])
def alerts(
    db: DbSession, user: Annotated[TokenData, Depends(require_role(Role.VIEWER))],
    active_only: bool = True, limit: int = Query(200, le=1000),
) -> list[Alert]:
    q = select(Alert).order_by(Alert.created_at.desc())
    if active_only:
        q = q.where(Alert.resolved_at.is_(None))
    return db.exec(q.limit(limit)).all()


@app.get("/api/predictions", tags=["dashboard"])
def predictions(
    db: DbSession, user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]
) -> list[dict]:
    latest = db.exec(
        select(RulEstimate.equipment_tag, func.max(RulEstimate.ts)).group_by(RulEstimate.equipment_tag)
    ).all()
    out = []
    for tag, ts in latest:
        r = db.exec(
            select(RulEstimate).where(RulEstimate.equipment_tag == tag, RulEstimate.ts == ts)
        ).first()
        eq = db.exec(select(Equipment).where(Equipment.tag == tag)).first()
        if r and eq:
            out.append({
                "tag": tag, "name": eq.name, "criticality": eq.criticality,
                "predicted_rul_hours": r.predicted_rul_hours, "confidence": r.confidence,
                "predicted_failure_at": r.predicted_failure_at, "health_score": r.health_score,
            })
    return sorted(out, key=lambda x: x["predicted_rul_hours"])


# ------------------------------------------------------------------ sensor health (3-light)
@app.get("/api/sensor-health", tags=["dashboard"])
def sensor_health(
    db: DbSession, user: Annotated[TokenData, Depends(require_role(Role.VIEWER))],
    color: str | None = None, kind: str | None = None, limit: int = 3000,
) -> dict:
    sq = select(Sensor)
    if color:
        sq = sq.where(Sensor.health_status == color)
    if kind:
        sq = sq.where(Sensor.kind == kind)
    sensors = db.exec(sq.limit(limit)).all()
    cameras = db.exec(select(Camera)).all()
    return {
        "sensors": [
            {"tag": s.tag, "kind": s.kind, "unit": s.unit_of_measure, "status": s.health_status,
             "range": [s.range_min, s.range_max]}
            for s in sensors
        ],
        "cameras": [
            {"tag": c.tag, "kind": c.kind, "unit": c.unit_of_measure, "status": c.health_status}
            for c in cameras
        ],
        "summary": {
            "green": sum(1 for s in sensors if s.health_status == "green"),
            "yellow": sum(1 for s in sensors if s.health_status == "yellow"),
            "red": sum(1 for s in sensors if s.health_status == "red"),
        },
    }


# ------------------------------------------------------------------ auto operation / economics / reports (proxy)
@app.get("/api/auto-operation/actions", tags=["dashboard"])
async def ao_actions(status: str | None = None,
                     user: Annotated[TokenData, Depends(require_role(Role.VIEWER))] = None) -> list:
    ao = auto_operation()
    try:
        return await ao.get("/actions", params={"status": status} if status else None)
    finally:
        await ao.aclose()


@app.get("/api/auto-operation/stats", tags=["dashboard"])
async def ao_stats(user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]) -> dict:
    ao = auto_operation()
    try:
        return await ao.get("/stats")
    finally:
        await ao.aclose()


@app.post("/api/auto-operation/actions/{action_id}/{decision}", tags=["dashboard"])
async def ao_decide(
    action_id: int, decision: str, request: Request,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
) -> dict:
    if decision not in {"approve", "reject"}:
        from fastapi import HTTPException
        raise HTTPException(400, "تصمیم نامعتبر")
    ao = auto_operation()
    try:
        auth = request.headers.get("authorization")
        return await ao.post(
            f"/actions/{action_id}/{decision}",
            headers={"Authorization": auth} if auth else None,
        )
    finally:
        await ao.aclose()


@app.post("/api/auto-operation/control/{tag}/{action}", tags=["dashboard"])
async def ao_control(
    tag: str, action: str, request: Request,
    user: Annotated[TokenData, Depends(require_role(Role.OPERATOR))],
) -> dict:
    if action not in {"start", "stop", "changeover"}:
        from fastapi import HTTPException
        raise HTTPException(400, "اقدام نامعتبر")
    ao = auto_operation()
    try:
        auth = request.headers.get("authorization")
        return await ao.post(
            f"/control/{tag}/{action}", json={},
            headers={"Authorization": auth} if auth else None,
        )
    finally:
        await ao.aclose()


@app.get("/api/economics/live", tags=["dashboard"])
async def economics_live(user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]) -> dict:
    ec = economics()
    try:
        return await ec.get("/live")
    finally:
        await ec.aclose()


@app.get("/api/economics/history", tags=["dashboard"])
async def economics_history(hours: int = 24,
                            user: Annotated[TokenData, Depends(require_role(Role.MANAGER))] = None) -> list:
    ec = economics()
    try:
        return await ec.get("/history", params={"hours": hours})
    finally:
        await ec.aclose()


@app.get("/api/reports", tags=["dashboard"])
async def reports_list(kind: str | None = None,
                       user: Annotated[TokenData, Depends(require_role(Role.VIEWER))] = None) -> list:
    rp = reporting()
    try:
        return await rp.get("/reports", params={"kind": kind} if kind else None)
    finally:
        await rp.aclose()
