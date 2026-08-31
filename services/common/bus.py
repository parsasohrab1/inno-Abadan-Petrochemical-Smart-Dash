"""باس رویداد مبتنی بر Kafka (aiokafka) با مدیریت خطای مقاوم.

اگر بروکر در دسترس نباشد، تولیدکننده رویدادها را در صف داخلی نگه می‌دارد و
دوباره تلاش می‌کند؛ سرویس متوقف نمی‌شود (کمک به NFR-06 در دسترس‌بودن).
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from services.common.config import get_settings
from services.common.logging import get_logger

log = get_logger("common.bus")
_settings = get_settings()


def _dumps(v: Any) -> bytes:
    return json.dumps(v, default=str, ensure_ascii=False).encode()


class EventBus:
    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self._producer: AIOKafkaProducer | None = None
        self._pending: list[tuple[str, dict, str | None]] = []
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=_settings.kafka_bootstrap_servers,
            client_id=self.client_id,
            value_serializer=_dumps,
            key_serializer=lambda k: k.encode() if k else None,
            enable_idempotence=True,
            linger_ms=20,
        )
        try:
            await self._producer.start()
            log.info("bus.producer.started", client_id=self.client_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("bus.producer.unavailable", error=str(exc))
            self._producer = None

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def publish(self, topic: str, payload: dict, key: str | None = None) -> None:
        async with self._lock:
            self._pending.append((topic, payload, key))
            await self._flush()

    async def _flush(self) -> None:
        if not self._producer:
            await self.start()
        if not self._producer:
            return
        still: list[tuple[str, dict, str | None]] = []
        for topic, payload, key in self._pending:
            try:
                await self._producer.send_and_wait(topic, payload, key=key)
            except Exception as exc:  # noqa: BLE001
                log.warning("bus.publish.retry", topic=topic, error=str(exc))
                still.append((topic, payload, key))
        self._pending = still


async def consume(
    topics: list[str],
    group_id: str,
    handler: Callable[[str, dict], Awaitable[None]],
    *,
    from_beginning: bool = False,
) -> None:
    """حلقه‌ی مصرف پایدار — با قطع بروکر دوباره تلاش می‌کند."""
    while True:
        consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=_settings.kafka_bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda b: json.loads(b.decode()),
            auto_offset_reset="earliest" if from_beginning else "latest",
            enable_auto_commit=True,
        )
        try:
            await consumer.start()
            log.info("bus.consumer.started", group=group_id, topics=topics)
            async for msg in consumer:
                try:
                    await handler(msg.topic, msg.value)
                except Exception:  # noqa: BLE001
                    log.exception("bus.handler.error", topic=msg.topic)
        except Exception as exc:  # noqa: BLE001
            log.warning("bus.consumer.reconnect", group=group_id, error=str(exc))
            await asyncio.sleep(5)
        finally:
            await consumer.stop()


async def stream(topics: list[str], group_id: str) -> AsyncIterator[tuple[str, dict]]:
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=_settings.kafka_bootstrap_servers,
        group_id=group_id,
        value_deserializer=lambda b: json.loads(b.decode()),
        auto_offset_reset="latest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            yield msg.topic, msg.value
    finally:
        await consumer.stop()
