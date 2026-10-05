"""MQTT → Kafka bridge for real edge sensors (when the simulator is off).

MQTT messages are expected to be published on `abadan/edge/<kind>/<sensor_tag>` with a JSON payload
containing at least `equipment_tag`, `value`, `unit`, `ts`.
"""
from __future__ import annotations

import json

from asyncio_mqtt import Client

from services.common.bus import EventBus
from services.common.config import get_settings
from services.common.logging import get_logger

log = get_logger("data-acquisition.mqtt")
_settings = get_settings()

_KIND_TOPIC = {
    "vibration": _settings.kafka_topic_vibration,
    "acoustic": _settings.kafka_topic_acoustic,
    "process": _settings.kafka_topic_process,
    "device_health": "telemetry.device_health",
}


async def run() -> None:
    bus = EventBus("data-acquisition-mqtt")
    await bus.start()
    async with Client(_settings.mqtt_host, port=_settings.mqtt_port) as client:
        await client.subscribe(f"{_settings.mqtt_base_topic}/#")
        log.info("mqtt.bridge.started", base=_settings.mqtt_base_topic)
        async with client.messages() as messages:
            async for msg in messages:
                try:
                    parts = msg.topic.value.split("/")
                    kind = parts[2] if len(parts) > 2 else "process"
                    payload = json.loads(msg.payload)
                    topic = _KIND_TOPIC.get(kind, _settings.kafka_topic_process)
                    await bus.publish(topic, payload, key=payload.get("equipment_tag"))
                except Exception:  # noqa: BLE001
                    log.exception("mqtt.bridge.bad_message", topic=msg.topic.value)
