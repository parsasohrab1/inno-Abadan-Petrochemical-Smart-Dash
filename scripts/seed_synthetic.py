"""Generate and load the initial synthetic data — README §10.

- Build the asset hierarchy + sensor/camera mapping (services.asset_registry.seed)
- Generate initial diagnosis/RUL/sensor-health history to populate the dashboard before the live stream
Run: python scripts/seed_synthetic.py
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlmodel import select

from ml.datagen.sensor_health import next_status, synth_health_metrics
from ml.datagen.vibration import WaveformSpec, degrade_severity, synth_waveform
from ml.features.extract import extract_features
from ml.models.fault_classifier import FaultClassifier
from services.asset_registry import seed
from services.common.config import get_settings
from services.common.db import init_db, session_scope
from services.common.domain.enums import FaultType, HealthColor
from services.common.domain.health import (
    equipment_color,
    evaluate_device_health,
    health_score_from,
)
from services.common.domain.models import (
    Diagnosis,
    DeviceHealthSnapshot,
    Equipment,
    RulEstimate,
    Sensor,
)
from services.common.logging import get_logger

log = get_logger("seed")
RNG = np.random.default_rng(1348)
PYRNG = random.Random(1348)


def main() -> None:
    settings = get_settings()
    init_db()
    with session_scope() as s:
        result = seed.build(s)
    log.info("seed.assets", **result)

    clf = FaultClassifier.load(settings.model_registry_path)
    log.info("seed.classifier", kind=type(clf).__name__)

    with session_scope() as s:
        equipment = s.exec(select(Equipment)).all()
        sensors = s.exec(select(Sensor)).all()

    now = datetime.now(timezone.utc)

    # --- diagnosis and RUL history for the past 30 days (one point per day) ---
    with session_scope() as s:
        for eq in equipment:
            faulty = PYRNG.random() < 0.22
            fault = (PYRNG.choice([f for f in FaultType if f != FaultType.NORMAL])
                     if faulty else FaultType.NORMAL)
            ttf = PYRNG.uniform(300, 1500)
            onset_day = PYRNG.randint(2, 26) if faulty else 99
            for day in range(30):
                ts = now - timedelta(days=30 - day)
                hours_in = max(0.0, (day - onset_day) * 24)
                severity = degrade_severity(hours_in, ttf) if faulty and day >= onset_day else 0.0
                spec = WaveformSpec(rpm=eq.rpm_nominal or 1480.0)
                wave = synth_waveform(fault if severity > 0 else FaultType.NORMAL, severity, spec, RNG)
                feats = extract_features(wave, spec.fs, spec.rpm)
                pred_fault, pred_sev, conf = clf.predict(feats)
                s.add(Diagnosis(equipment_tag=eq.tag, ts=ts, fault_type=pred_fault,
                                severity=round(pred_sev, 4), confidence=round(conf, 4),
                                model_version=type(clf).__name__))
                rul_hours = max(200.0, (1 - pred_sev) ** 2 * PYRNG.uniform(15000, 60000))
                score = health_score_from(pred_sev, rul_hours)
                s.add(RulEstimate(equipment_tag=eq.tag, ts=ts,
                                  predicted_rul_hours=round(rul_hours, 1), confidence=round(conf, 3),
                                  predicted_failure_at=ts + timedelta(hours=rul_hours),
                                  health_score=score))
            # current equipment state
            eq_row = s.exec(select(Equipment).where(Equipment.id == eq.id)).first()
            last_sev = degrade_severity(max(0.0, (30 - onset_day) * 24), ttf) if faulty else 0.0
            rul_now = max(150.0, (1 - last_sev) ** 2 * 40000)
            eq_row.health_score = health_score_from(last_sev, rul_now)
            eq_row.health_color = equipment_color(eq_row.health_score)
            s.add(eq_row)
    log.info("seed.history.diagnosis_rul.done", equipment=len(equipment))

    # --- 30-day sensor health chain ---
    with session_scope() as s:
        for sensor in sensors:
            status = HealthColor(PYRNG.choices(
                ["green", "yellow", "red"], weights=[0.92, 0.06, 0.02])[0])
            for day in range(0, 30, 2):
                ts = now - timedelta(days=30 - day)
                status = next_status(status, RNG)
                m = synth_health_metrics(status, RNG)
                res = evaluate_device_health(m)
                s.add(DeviceHealthSnapshot(
                    device_tag=sensor.tag, device_type="sensor", ts=ts, status=res.status,
                    supply_voltage=round(m.supply_voltage, 2), loop_current_ma=round(m.loop_current_ma, 2),
                    snr_db=round(m.snr_db, 1), calibration_drift_pct=round(m.calibration_drift_pct, 2),
                    comm_latency_ms=round(m.comm_latency_ms, 1), device_temp_c=round(m.device_temp_c, 1),
                    reasons="; ".join(res.reasons),
                ))
            sensor_row = s.exec(select(Sensor).where(Sensor.id == sensor.id)).first()
            sensor_row.health_status = res.status
            s.add(sensor_row)
    log.info("seed.history.sensor_health.done", sensors=len(sensors))
    log.info("seed.complete")


if __name__ == "__main__":
    main()
