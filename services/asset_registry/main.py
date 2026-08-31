"""API ثبت دارایی — CRUD سلسله‌مراتب + پرس‌وجوی نگاشت سنسور/دوربین."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlmodel import Session, select

from services.asset_registry import seed
from services.common.db import get_session, init_db, session_scope
from services.common.domain.models import (
    Camera,
    CameraCoverage,
    Component,
    Equipment,
    MaintenanceRecord,
    Plant,
    ProductionLine,
    Sensor,
    SensorMount,
    Unit,
)
from services.common.logging import get_logger
from services.common.service import create_app

log = get_logger("asset-registry")

DbSession = Annotated[Session, Depends(get_session)]


async def _startup() -> None:
    init_db()
    with session_scope() as s:
        result = seed.build(s)
    log.info("asset-registry.seed", **result)


app = create_app("asset-registry", on_startup=_startup)


# ------------------------------------------------------------------ hierarchy
@app.get("/plant", tags=["hierarchy"])
def get_plant(db: DbSession) -> Plant:
    plant = db.exec(select(Plant)).first()
    if not plant:
        raise HTTPException(404, "مجتمع تعریف نشده — seed اجرا شود")
    return plant


@app.get("/units", tags=["hierarchy"])
def list_units(db: DbSession) -> list[Unit]:
    return db.exec(select(Unit)).all()


@app.get("/units/{unit_id}/lines", tags=["hierarchy"])
def list_lines(unit_id: int, db: DbSession) -> list[ProductionLine]:
    return db.exec(select(ProductionLine).where(ProductionLine.unit_id == unit_id)).all()


@app.get("/lines/{line_id}/equipment", tags=["hierarchy"])
def list_line_equipment(line_id: int, db: DbSession) -> list[Equipment]:
    return db.exec(select(Equipment).where(Equipment.line_id == line_id)).all()


@app.get("/equipment", tags=["equipment"])
def list_equipment(
    db: DbSession,
    unit_code: str | None = None,
    etype: str | None = None,
    run_state: str | None = None,
) -> list[Equipment]:
    q = select(Equipment)
    if etype:
        q = q.where(Equipment.etype == etype)
    if run_state:
        q = q.where(Equipment.run_state == run_state)
    rows = db.exec(q).all()
    if unit_code:
        line_ids = {
            l.id
            for l in db.exec(
                select(ProductionLine)
                .join(Unit, ProductionLine.unit_id == Unit.id)
                .where(Unit.code == unit_code)
            ).all()
        }
        rows = [e for e in rows if e.line_id in line_ids]
    return rows


@app.get("/equipment/{tag}", tags=["equipment"])
def get_equipment(tag: str, db: DbSession) -> Equipment:
    eq = db.exec(select(Equipment).where(Equipment.tag == tag)).first()
    if not eq:
        raise HTTPException(404, f"تجهیز {tag} یافت نشد")
    return eq


@app.get("/equipment/{tag}/full", tags=["equipment"])
def get_equipment_full(tag: str, db: DbSession) -> dict:
    """تجهیز + اجزا + همه‌ی سنسورها و دوربین‌های مرتبط (با واحد اندازه‌گیری)."""
    eq = db.exec(select(Equipment).where(Equipment.tag == tag)).first()
    if not eq:
        raise HTTPException(404, f"تجهیز {tag} یافت نشد")
    components = db.exec(select(Component).where(Component.equipment_id == eq.id)).all()
    mounts = db.exec(select(SensorMount).where(SensorMount.equipment_id == eq.id)).all()
    sensors = []
    for m in mounts:
        s = db.get(Sensor, m.sensor_id)
        if s:
            sensors.append({
                "tag": s.tag, "kind": s.kind, "unit": s.unit_of_measure,
                "range": [s.range_min, s.range_max], "axis": m.axis,
                "measured_quantity": m.measured_quantity, "health": s.health_status,
            })
    covs = db.exec(select(CameraCoverage).where(CameraCoverage.equipment_id == eq.id)).all()
    cameras = []
    for c in covs:
        cam = db.get(Camera, c.camera_id)
        if cam:
            cameras.append({
                "tag": cam.tag, "kind": cam.kind, "unit": cam.unit_of_measure,
                "purpose": c.purpose, "health": cam.health_status,
            })
    return {
        "equipment": eq,
        "components": components,
        "sensors": sensors,
        "cameras": cameras,
    }


@app.get("/equipment/{tag}/maintenance", tags=["equipment"])
def equipment_maintenance(tag: str, db: DbSession) -> list[MaintenanceRecord]:
    eq = get_equipment(tag, db)
    return db.exec(
        select(MaintenanceRecord).where(MaintenanceRecord.equipment_id == eq.id)
    ).all()


# ------------------------------------------------------------------ sensors / cameras
@app.get("/sensors", tags=["sensors"])
def list_sensors(
    db: DbSession,
    kind: str | None = None,
    health: str | None = None,
    limit: int = Query(2000, le=5000),
) -> list[Sensor]:
    q = select(Sensor)
    if kind:
        q = q.where(Sensor.kind == kind)
    if health:
        q = q.where(Sensor.health_status == health)
    return db.exec(q.limit(limit)).all()


@app.get("/sensors/{tag}/context", tags=["sensors"])
def sensor_context(tag: str, db: DbSession) -> dict:
    s = db.exec(select(Sensor).where(Sensor.tag == tag)).first()
    if not s:
        raise HTTPException(404, "سنسور یافت نشد")
    mount = db.exec(select(SensorMount).where(SensorMount.sensor_id == s.id)).first()
    eq = db.get(Equipment, mount.equipment_id) if mount and mount.equipment_id else None
    return {"sensor": s, "mount": mount, "equipment": eq}


@app.get("/cameras", tags=["cameras"])
def list_cameras(db: DbSession, kind: str | None = None, health: str | None = None) -> list[Camera]:
    q = select(Camera)
    if kind:
        q = q.where(Camera.kind == kind)
    if health:
        q = q.where(Camera.health_status == health)
    return db.exec(q).all()


@app.get("/coverage/unmonitored", tags=["cameras"])
def unmonitored(db: DbSession) -> dict:
    """بازرسی الزام کاربر: تجهیز/خطی که سنسور یا دوربین ندارد."""
    eq_with_sensor = {m.equipment_id for m in db.exec(select(SensorMount)).all() if m.equipment_id}
    eq_with_cam = {c.equipment_id for c in db.exec(select(CameraCoverage)).all() if c.equipment_id}
    line_with_cam = {c.line_id for c in db.exec(select(CameraCoverage)).all() if c.line_id}
    equipment = db.exec(select(Equipment)).all()
    lines = db.exec(select(ProductionLine)).all()
    return {
        "equipment_without_sensor": [e.tag for e in equipment if e.id not in eq_with_sensor],
        "equipment_without_camera": [e.tag for e in equipment if e.id not in eq_with_cam],
        "lines_without_camera": [l.code for l in lines if l.id not in line_with_cam],
    }


# ------------------------------------------------------------------ mutations
@app.patch("/equipment/{tag}/state", tags=["equipment"])
def set_run_state(tag: str, state: str, db: DbSession) -> Equipment:
    eq = get_equipment(tag, db)
    eq.run_state = state  # type: ignore[assignment]
    db.add(eq)
    return eq


@app.post("/equipment/{tag}/maintenance", tags=["equipment"], status_code=201)
def add_maintenance(tag: str, record: MaintenanceRecord, db: DbSession) -> MaintenanceRecord:
    eq = get_equipment(tag, db)
    record.equipment_id = eq.id
    db.add(record)
    db.flush()
    return record


@app.get("/stats", tags=["meta"])
def stats(db: DbSession) -> dict:
    return {
        "units": len(db.exec(select(Unit)).all()),
        "lines": len(db.exec(select(ProductionLine)).all()),
        "equipment": len(db.exec(select(Equipment)).all()),
        "sensors": len(db.exec(select(Sensor)).all()),
        "cameras": len(db.exec(select(Camera)).all()),
    }
