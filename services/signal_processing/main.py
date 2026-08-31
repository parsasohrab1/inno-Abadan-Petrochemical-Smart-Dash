"""مصرف قاب‌های ارتعاش → پاک‌سازی → استخراج ویژگی → انتشار روی analytics.features.

خروجی ISO 13374 (Data Manipulation + State Detection پایه). ویژگی‌های کلیدی در
InfluxDB برای روندنمایی ۷/۳۰/۹۰ روزه (FR-13) ذخیره می‌شوند.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import numpy as np

from ml.features.extract import extract_features
from services.common.bus import EventBus, consume
from services.common.config import get_settings
from services.common.logging import get_logger
from services.common.tsdb import tsdb
from services.signal_processing.denoise import clean

log = get_logger("signal-processing")
_settings = get_settings()
_bus = EventBus("signal-processing")

_KEY_FEATURES = ("rms", "peak", "crest_factor", "kurtosis", "envelope_kurtosis", "hf_energy_ratio")


async def _handle(topic: str, msg: dict) -> None:
    samples = msg.get("samples")
    if not samples:
        return
    fs = float(msg.get("sample_rate_hz", 25600.0))
    rpm = msg.get("rpm")
    x = np.asarray(samples, dtype=float)

    x_clean = clean(x, fs)
    feats = extract_features(x_clean, fs, rpm)

    now = datetime.now(timezone.utc).isoformat()
    event = {
        "equipment_tag": msg["equipment_tag"],
        "sensor_tag": msg["sensor_tag"],
        "axis": msg.get("axis", "X"),
        "ts": now,
        "rpm": rpm,
        "features": feats,
        "source_unit": msg.get("unit", "g"),
    }
    await _bus.publish(_settings.kafka_topic_features, event, key=msg["equipment_tag"])

    tsdb.write_reading(
        "vibration_features",
        {"equipment_tag": msg["equipment_tag"], "sensor_tag": msg["sensor_tag"], "axis": msg.get("axis", "X")},
        {k: feats[k] for k in _KEY_FEATURES if k in feats},
    )


async def main() -> None:
    await _bus.start()
    await consume(
        [_settings.kafka_topic_vibration],
        group_id="signal-processing",
        handler=_handle,
    )


if __name__ == "__main__":
    asyncio.run(main())
