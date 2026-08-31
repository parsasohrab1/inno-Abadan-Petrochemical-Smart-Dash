"""تست‌های واحد منطق دامنه — بدون نیاز به پایگاه‌داده یا Kafka."""
from __future__ import annotations

import numpy as np

from ml.datagen.sensor_health import verify_rules_consistency
from ml.datagen.vibration import WaveformSpec, degrade_severity, synth_waveform
from ml.features.extract import FEATURE_ORDER, extract_features, to_vector
from services.common.domain.enums import FaultType
from services.common.domain.faults import SIGNATURES
from services.common.domain.health import (
    DeviceHealthInputs,
    equipment_color,
    evaluate_device_health,
)
from services.common.economics import (
    LineProduction,
    avoided_downtime_value,
    compute_profit_rate,
    load_price_book,
)


def test_sixteen_fault_signatures():
    non_normal = [f for f in SIGNATURES if f is not FaultType.NORMAL]
    assert len(non_normal) == 16
    assert set(SIGNATURES) == set(FaultType)


def test_feature_vector_shape_and_finiteness():
    w = synth_waveform(FaultType.UNBALANCE, 0.6, WaveformSpec(rpm=2960), np.random.default_rng(0))
    feats = extract_features(w, 25600, 2960)
    vec = to_vector(feats)
    assert vec.shape == (len(FEATURE_ORDER),)
    assert np.isfinite(vec).all()


def test_unbalance_raises_1x_amplitude():
    rng = np.random.default_rng(1)
    healthy = extract_features(synth_waveform(FaultType.NORMAL, 0.0, WaveformSpec(rpm=2960), rng), 25600, 2960)
    faulty = extract_features(synth_waveform(FaultType.UNBALANCE, 0.9, WaveformSpec(rpm=2960), rng), 25600, 2960)
    assert faulty["rms"] > healthy["rms"]


def test_degrade_severity_monotonic():
    xs = [degrade_severity(h, 1000) for h in range(0, 1001, 100)]
    assert xs == sorted(xs)
    assert xs[0] == 0.0 and abs(xs[-1] - 1.0) < 1e-9


def test_device_health_three_light():
    assert evaluate_device_health(DeviceHealthInputs()).status.value == "green"
    assert evaluate_device_health(DeviceHealthInputs(snr_db=15)).status.value == "yellow"
    assert evaluate_device_health(DeviceHealthInputs(comm_gap_s=120)).status.value == "red"


def test_sensor_health_generator_matches_rules():
    assert verify_rules_consistency(800) >= 0.98


def test_equipment_color_thresholds():
    assert equipment_color(90).value == "green"
    assert equipment_color(60).value == "yellow"
    assert equipment_color(20).value == "red"


def test_profit_and_savings_positive():
    pb = load_price_book()
    pr = compute_profit_rate([LineProduction("PVC-A", "PVC", 3.4, 800)], pb)
    assert pr.profit_rate_usd_per_hour > 0
    assert avoided_downtime_value(8, "PVC", pb) > 0
