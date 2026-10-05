"""Consume telemetry.device_health → record a snapshot + update the sensor/camera color state.

When going red, an alert is issued (reduced data reliability — README §8-2).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlmodel import select

from services.common.bus import EventBus, consume
from services.common.config import get_settings
from services.common.db import init_db, session_scope
from services.common.domain.enums import HealthColor
from services.common.domain.models import Camera, DeviceHealthSnapshot, Sensor
from services.common.logging import get_logger
from services.common.tsdb import tsdb

log = get_logger("sensor-health")
_settings = get_settings()
_bus = EventBus("sensor-health")
_last_status: dict[str, str] = {}

_COLOR_NUM = {HealthColor.GREEN: 0, HealthColor.YELLOW: 1, HealthColor.RED: 2}


async def _handle(topic: str, msg: dict) -> None:
    tag = msg["device_tag"]
    dtype = msg.get("device_type", "sensor")
    status = HealthColor(msg["status"])
    m = msg.get("metrics", {})
    now = datetime.now(timezone.utc)

    with session_scope() as s:
        s.add(DeviceHealthSnapshot(
            device_tag=tag, device_type=dtype, ts=now, status=status,
            supply_voltage=m.get("supply_voltage"), loop_current_ma=m.get("loop_current_ma"),
            snr_db=m.get("snr_db"), calibration_drift_pct=m.get("calibration_drift_pct"),
            comm_latency_ms=m.get("comm_latency_ms"), device_temp_c=m.get("device_temp_c"),
            reasons="; ".join(msg.get("reasons", [])),
        ))
        if dtype == "camera":
            dev = s.exec(select(Camera).where(Camera.tag == tag)).first()
        else:
            dev = s.exec(select(Sensor).where(Sensor.tag == tag)).first()
        if dev:
            dev.health_status = status
            s.add(dev)

    tsdb.write_reading("device_health", {"device_tag": tag, "device_type": dtype},
                       {"status_num": _COLOR_NUM[status], **{k: float(v) for k, v in m.items()}})

    prev = _last_status.get(tag)
    _last_status[tag] = status.value
    if status == HealthColor.RED and prev != HealthColor.RED.value:
        await _bus.publish(
            _settings.kafka_topic_alerts,
            {
                "code": "SENSOR_FAULT",
                "title": f"{'Camera' if dtype == 'camera' else 'Sensor'} {tag} failure",
                "severity": "major",
                "device_tag": tag,
                "ts": now.isoformat(),
                "is_predictive": False,
                "description": "; ".join(msg.get("reasons", [])) or "Invalid data",
            },
            key=tag,
        )
        log.info("sensor-health.red", device=tag, reasons=msg.get("reasons"))


async def main() -> None:
    init_db()
    await _bus.start()
    await consume(["telemetry.device_health"], "sensor-health", _handle)


if __name__ == "__main__":
    asyncio.run(main())
