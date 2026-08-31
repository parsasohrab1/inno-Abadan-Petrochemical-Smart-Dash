"""API گزارش‌دهی + زمان‌بند تولید خودکار (FR-19)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, HTTPException
from sqlmodel import Session, select

from services.common.db import get_session, init_db
from services.common.domain.enums import Role
from services.common.domain.models import Report
from services.common.logging import get_logger
from services.common.security import TokenData, require_role
from services.common.service import create_app
from services.reporting.generators import generate

log = get_logger("reporting")
DbSession = Annotated[Session, Depends(get_session)]
_scheduler = AsyncIOScheduler(timezone="UTC")


def _job(kind: str) -> None:
    try:
        r = generate(kind)
        log.info("reporting.generated", kind=kind, id=r.id, summary=r.summary)
    except Exception:  # noqa: BLE001
        log.exception("reporting.job.failed", kind=kind)


async def _startup() -> None:
    init_db()
    _scheduler.add_job(_job, CronTrigger(hour=1, minute=0), args=["daily"], id="daily")
    _scheduler.add_job(_job, CronTrigger(day_of_week="sat", hour=2), args=["weekly"], id="weekly")
    _scheduler.add_job(_job, CronTrigger(day=1, hour=3), args=["monthly"], id="monthly")
    _scheduler.add_job(_job, CronTrigger(day=1, hour=4), args=["cost_benefit"], id="cost_benefit")
    _scheduler.add_job(_job, CronTrigger(day_of_week="sun", hour=5), args=["ai_performance"], id="ai_perf")
    _scheduler.start()
    log.info("reporting.scheduler.started", jobs=[j.id for j in _scheduler.get_jobs()])


app = create_app("reporting", on_startup=_startup)


@app.get("/reports", tags=["reports"])
def list_reports(db: DbSession, kind: str | None = None, limit: int = 50) -> list[Report]:
    q = select(Report).order_by(Report.created_at.desc())
    if kind:
        q = q.where(Report.kind == kind)
    return db.exec(q.limit(limit)).all()


@app.get("/reports/{report_id}", tags=["reports"])
def get_report(report_id: int, db: DbSession) -> dict:
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "گزارش یافت نشد")
    return {**r.model_dump(), "payload": json.loads(r.payload_json or "{}")}


@app.post("/reports/generate", tags=["reports"])
def generate_now(
    kind: str,
    user: Annotated[TokenData, Depends(require_role(Role.ENGINEER))],
) -> dict:
    if kind not in {"daily", "weekly", "monthly", "cost_benefit", "ai_performance"}:
        raise HTTPException(400, "نوع گزارش نامعتبر")
    r = generate(kind)
    return {**r.model_dump(), "payload": json.loads(r.payload_json or "{}")}
