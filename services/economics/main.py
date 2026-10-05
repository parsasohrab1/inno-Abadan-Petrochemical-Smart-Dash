"""Economics service API — instantaneous profit and savings for the manager."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, select

from services.common.db import get_session, init_db
from services.common.domain.enums import Role
from services.common.domain.models import EconomicsSnapshot
from services.common.economics import DEFAULT_PRICE_BOOK
from services.common.security import TokenData, require_role
from services.common.service import create_app
from services.economics.calculator import calculator

DbSession = Annotated[Session, Depends(get_session)]


async def _startup() -> None:
    init_db()
    asyncio.create_task(calculator.run())


app = create_app("economics", on_startup=_startup)


@app.get("/live", tags=["economics"])
def live(user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]) -> dict:
    """Instantaneous profit and savings — the top card of the management dashboard."""
    return calculator.snapshot_dict()


@app.get("/history", tags=["economics"])
def history(db: DbSession, hours: int = 24, limit: int = 500) -> list[EconomicsSnapshot]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return db.exec(
        select(EconomicsSnapshot)
        .where(EconomicsSnapshot.ts >= since)
        .order_by(EconomicsSnapshot.ts.desc())
        .limit(limit)
    ).all()


@app.get("/breakdown", tags=["economics"])
def breakdown(user: Annotated[TokenData, Depends(require_role(Role.MANAGER))]) -> dict:
    return calculator._last_breakdown or {}


@app.get("/pricebook", tags=["economics"])
def get_pricebook() -> dict:
    return calculator.price_book


@app.put("/pricebook", tags=["economics"])
def put_pricebook(
    new_book: dict,
    user: Annotated[TokenData, Depends(require_role(Role.MANAGER))],
) -> dict:
    calculator.price_book = {**DEFAULT_PRICE_BOOK, **new_book}
    return calculator.price_book
