"""Consume features → fault diagnosis → publish on analytics.diagnosis + store in the DB.

Also consumes telemetry.acoustic for leak detection (FR-10).
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict, deque
from datetime import datetime, timezone

from sqlmodel import select

from ml.models.fault_classifier import FaultClassifier
from services.common.bus import EventBus, consume
from services.common.config import get_settings
from services.common.db import init_db, session_scope
from services.common.domain.enums import FaultType
from services.common.domain.models import Diagnosis
from services.common.logging import get_logger
from services.common.tsdb import tsdb

log = get_logger("ai-engine")
_settings = get_settings()
_bus = EventBus("ai-engine")
_clf = FaultClassifier.load(_settings.model_registry_path)

# per-equipment feature buffer (averaging over recent axes/frames)
_buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=6))
_ema_severity: dict[str, float] = defaultdict(float)
_last_fault: dict[str, FaultType] = {}


def _avg_features(items: list[dict]) -> dict[str, float]:
    keys = set().union(*(d.keys() for d in items))
    return {k: sum(d.get(k, 0.0) for d in items) / len(items) for k in keys}


async def _on_features(topic: str, msg: dict) -> None:
    tag = msg["equipment_tag"]
    _buffers[tag].append(msg["features"])
    if len(_buffers[tag]) < 3:
        return

    feats = _avg_features(list(_buffers[tag]))
    fault, severity, confidence = _clf.predict(feats)

    prev = _ema_severity[tag]
    _ema_severity[tag] = 0.7 * prev + 0.3 * severity
    smoothed = round(_ema_severity[tag], 4)

    changed = _last_fault.get(tag) != fault
    _last_fault[tag] = fault
    now = datetime.now(timezone.utc)

    tsdb.write_reading(
        "diagnosis",
        {"equipment_tag": tag, "fault_type": fault.value},
        {"severity": smoothed, "confidence": round(confidence, 4)},
    )

    # an event is emitted only when the fault or severity changes significantly
    if not changed and smoothed < 0.2:
        return

    event = {
        "equipment_tag": tag,
        "ts": now.isoformat(),
        "fault_type": fault.value,
        "severity": smoothed,
        "confidence": round(confidence, 4),
        "model_version": type(_clf).__name__,
        "contributing_features": {k: round(feats.get(k, 0), 4) for k in
                                  ("rms", "kurtosis", "crest_factor", "hf_energy_ratio", "ratio_2x_1x")},
    }
    await _bus.publish(_settings.kafka_topic_diagnosis, event, key=tag)

    with session_scope() as s:
        s.add(Diagnosis(
            equipment_tag=tag, ts=now, fault_type=fault, severity=smoothed,
            confidence=confidence, features_json=json.dumps(event["contributing_features"]),
            model_version=type(_clf).__name__,
        ))

    if changed:
        log.info("ai.diagnosis", equipment=tag, fault=fault.value, severity=smoothed, conf=round(confidence, 3))


async def _on_acoustic(topic: str, msg: dict) -> None:
    idx = msg.get("leak_index", 0.0)
    if idx < 0.25:
        return
    tag = msg["equipment_tag"]
    now = datetime.now(timezone.utc).isoformat()
    await _bus.publish(
        _settings.kafka_topic_alerts,
        {
            "code": "ACOUSTIC_LEAK",
            "title": f"Possible acoustic leak at {tag}",
            "severity": "major" if idx > 0.45 else "warning",
            "equipment_tag": tag,
            "ts": now,
            "is_predictive": False,
            "description": f"Ultrasonic energy index = {idx:.2f}",
        },
        key=tag,
    )
    tsdb.write_reading("acoustic", {"equipment_tag": tag}, {"leak_index": idx})


async def main() -> None:
    init_db()
    await _bus.start()
    log.info("ai-engine.model", classifier=type(_clf).__name__)
    await asyncio.gather(
        consume([_settings.kafka_topic_features], "ai-engine-features", _on_features),
        consume([_settings.kafka_topic_acoustic], "ai-engine-acoustic", _on_acoustic),
    )


if __name__ == "__main__":
    asyncio.run(main())
