"""Economics computation loop — each interval measures and stores the instantaneous profit and savings."""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

import numpy as np

from ml.datagen.process import line_flow_tph
from services.common.bus import consume
from services.common.clients import asset_registry, auto_operation
from services.common.config import get_settings
from services.common.db import init_db, session_scope
from services.common.domain.models import EconomicsSnapshot
from services.common.economics import (
    LineProduction,
    SavingsBreakdown,
    compute_profit_rate,
    load_price_book,
)
from services.common.logging import get_logger

log = get_logger("economics.calc")
_settings = get_settings()


class EconomicsCalculator:
    def __init__(self, interval_s: float = 10.0) -> None:
        self.interval_s = interval_s
        self.price_book = load_price_book()
        self._t0 = time.monotonic()
        self._day = datetime.now(timezone.utc).date()
        self.profit_today = 0.0
        self.savings_today = 0.0
        self.savings_mtd = 0.0
        # realized savings from Auto Operation actions (event-driven)
        self._auto_savings_today = 0.0
        self._last_profit_rate = 0.0
        self._last_savings_rate = 0.0
        self._last_breakdown: dict = {}
        self._lines_cache: list[dict] = []
        self._cache_ts = 0.0

    # -------------------------------------------------- data
    async def _lines(self) -> list[dict]:
        if time.monotonic() - self._cache_ts < 60 and self._lines_cache:
            return self._lines_cache
        ar = asset_registry()
        try:
            units = await ar.get("/units")
            out: list[dict] = []
            for u in units:
                lines = await ar.get(f"/units/{u['id']}/lines")
                for ln in lines:
                    if not ln.get("product") or not ln.get("design_rate_tph"):
                        continue
                    eq = await ar.get("/equipment", params={"unit_code": u["code"], "limit": 5000})
                    line_eq = [e for e in eq if e["line_id"] == ln["id"]]
                    out.append({"line": ln, "equipment": line_eq})
            self._lines_cache = out
            self._cache_ts = time.monotonic()
        except Exception as exc:  # noqa: BLE001
            log.warning("economics.lines.unavailable", error=str(exc))
        finally:
            await ar.aclose()
        return self._lines_cache

    @staticmethod
    def _availability(equipment: list[dict]) -> float:
        if not equipment:
            return 1.0
        vals = []
        for e in equipment:
            if e.get("run_state") in {"stopped", "tripped", "maintenance"} and not e.get("has_spare"):
                vals.append(0.0)
            else:
                vals.append(float(e.get("health_score", 100.0)) / 100.0)
        return float(np.clip(np.mean(vals), 0.0, 1.0))

    # -------------------------------------------------- savings model
    async def _realized_auto_savings(self) -> float:
        ao = auto_operation()
        try:
            st = await ao.get("/stats")
            return float(st.get("realized_savings_usd", 0.0))
        except Exception:  # noqa: BLE001
            return self._auto_savings_today
        finally:
            await ao.aclose()

    def on_auto_action(self, msg: dict) -> None:
        if msg.get("status") == "success":
            self._auto_savings_today += float(msg.get("estimated_savings_usd", 0.0))

    # -------------------------------------------------- main loop
    async def tick(self) -> EconomicsSnapshot:
        self._roll_day()
        sim_seconds = time.monotonic() - self._t0
        lines_data = await self._lines()

        productions: list[LineProduction] = []
        energy_saving_rate = 0.0
        for ld in lines_data:
            ln = ld["line"]
            avail = self._availability(ld["equipment"])
            rate = line_flow_tph(ln["design_rate_tph"], sim_seconds, availability=avail)
            power = sum(float(e.get("rated_power_kw", 0)) * 0.6 for e in ld["equipment"])
            productions.append(LineProduction(
                line_code=ln["code"], product=ln["product"], rate_tph=rate, power_kw=power,
            ))
            # energy savings from load reduction due to preventive actions (approximation)
            energy_saving_rate += power * 0.02 * self.price_book["energy"]["electricity_usd_per_kwh"]

        profit = compute_profit_rate(productions, self.price_book)

        realized_auto = await self._realized_auto_savings()
        # current savings rate = instantaneous energy savings + amortization of today's realized savings over 24 hours
        savings_rate = round(energy_saving_rate + realized_auto / 24.0, 2)

        dt_h = self.interval_s / 3600.0
        self.profit_today += profit.profit_rate_usd_per_hour * dt_h
        self.savings_today = round(realized_auto + energy_saving_rate * (sim_seconds / 3600.0), 2)
        self.savings_mtd += savings_rate * dt_h

        self._last_profit_rate = profit.profit_rate_usd_per_hour
        self._last_savings_rate = savings_rate
        breakdown = {
            "revenue_rate_usd_per_hour": profit.revenue_rate_usd_per_hour,
            "cost_rate_usd_per_hour": profit.cost_rate_usd_per_hour,
            "profit_per_line": profit.per_line,
            "savings": SavingsBreakdown(
                energy_optimization_usd=round(energy_saving_rate, 2),
                planned_repair_saving_usd=round(realized_auto, 2),
                total_usd=round(realized_auto + energy_saving_rate, 2),
            ).__dict__,
        }
        self._last_breakdown = breakdown

        snap = EconomicsSnapshot(
            ts=datetime.now(timezone.utc),
            profit_rate_usd_per_hour=profit.profit_rate_usd_per_hour,
            savings_rate_usd_per_hour=savings_rate,
            profit_today_usd=round(self.profit_today, 2),
            savings_today_usd=round(self.savings_today, 2),
            savings_mtd_usd=round(self.savings_mtd, 2),
            breakdown_json=json.dumps(breakdown, ensure_ascii=False, default=str),
        )
        with session_scope() as s:
            s.add(snap)
        return snap

    def _roll_day(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._day:
            self._day = today
            self.profit_today = 0.0
            self.savings_today = 0.0
            self._auto_savings_today = 0.0

    def snapshot_dict(self) -> dict:
        return {
            "profit_rate_usd_per_hour": self._last_profit_rate,
            "savings_rate_usd_per_hour": self._last_savings_rate,
            "profit_today_usd": round(self.profit_today, 2),
            "savings_today_usd": round(self.savings_today, 2),
            "savings_mtd_usd": round(self.savings_mtd, 2),
            "breakdown": self._last_breakdown,
            "currency": "USD",
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    async def run(self) -> None:
        init_db()
        asyncio.create_task(self._consume_actions())
        while True:
            try:
                await self.tick()
            except Exception:  # noqa: BLE001
                log.exception("economics.tick.error")
            await asyncio.sleep(self.interval_s)

    async def _consume_actions(self) -> None:
        async def handle(topic: str, msg: dict) -> None:
            self.on_auto_action(msg)

        await consume([_settings.kafka_topic_auto_ops], "economics", handle)


calculator = EconomicsCalculator()
