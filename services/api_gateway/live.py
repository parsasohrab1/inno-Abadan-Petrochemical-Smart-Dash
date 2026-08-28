"""پخش بلادرنگ به داشبرد از طریق WebSocket — تجمیع رویدادهای Kafka + نبض اقتصاد."""
from __future__ import annotations

import asyncio
import contextlib
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.common.bus import stream
from services.common.clients import economics
from services.common.config import get_settings
from services.common.logging import get_logger

log = get_logger("api-gateway.live")
_settings = get_settings()
router = APIRouter()


class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in self.clients:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


hub = Hub()


async def _pump_kafka() -> None:
    topics = [
        "events.alerts_inapp",
        _settings.kafka_topic_auto_ops,
        _settings.kafka_topic_diagnosis,
        "analytics.rul",
    ]
    channel = {
        "events.alerts_inapp": "alert",
        _settings.kafka_topic_auto_ops: "auto_action",
        _settings.kafka_topic_diagnosis: "diagnosis",
        "analytics.rul": "rul",
    }
    while True:
        try:
            async for topic, msg in stream(topics, "api-gateway-live"):
                await hub.broadcast({"channel": channel.get(topic, topic), "data": msg})
        except Exception as exc:  # noqa: BLE001
            log.warning("live.kafka.reconnect", error=str(exc))
            await asyncio.sleep(5)


async def _pump_economics() -> None:
    ec = economics()
    while True:
        try:
            data = await ec.get("/live")
            await hub.broadcast({"channel": "economics", "data": data})
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(5)


def start_pumps() -> None:
    asyncio.create_task(_pump_kafka())
    asyncio.create_task(_pump_economics())


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        while True:
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(ws.receive_text(), timeout=30)
    except WebSocketDisconnect:
        hub.disconnect(ws)
