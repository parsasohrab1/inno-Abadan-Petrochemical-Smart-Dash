"""Event bus contract (Kafka/MQTT) — JSON. Aligned with `packages/contracts/schemas`."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from services.common.domain.enums import FaultType, HealthColor, SignalQuality


class TelemetryReading(BaseModel):
    sensor_tag: str
    equipment_tag: str
    kind: str
    ts: datetime
    value: float
    unit: str                       # always accompanies the value (user requirement)
    quality: SignalQuality = SignalQuality.GOOD
    sensor_health: HealthColor = HealthColor.GREEN


class WaveformFrame(BaseModel):
    """Raw vibration/acoustic signal frame for FFT processing."""

    sensor_tag: str
    equipment_tag: str
    axis: str = "X"
    ts: datetime
    sample_rate_hz: float
    unit: str
    samples: list[float]
    rpm: float | None = None


class FeatureVector(BaseModel):
    equipment_tag: str
    sensor_tag: str
    ts: datetime
    rpm: float | None = None
    features: dict[str, float]       # rms, peak, crest_factor, kurtosis, band energies, ...
    spectrum_orders: dict[str, float] | None = None  # amplitude at multiples 0.5X..10X


class DiagnosisEvent(BaseModel):
    equipment_tag: str
    ts: datetime
    fault_type: FaultType
    severity: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    model_version: str = "v0"
    contributing_features: dict[str, float] | None = None


class RulEvent(BaseModel):
    equipment_tag: str
    ts: datetime
    predicted_rul_hours: float
    confidence: float
    predicted_failure_at: datetime | None = None
    health_score: float


class DeviceHealthEvent(BaseModel):
    device_tag: str
    device_type: str = "sensor"
    ts: datetime
    status: HealthColor
    reasons: list[str] = []
    metrics: dict[str, float] = {}


class AlertEvent(BaseModel):
    code: str
    title: str
    severity: str
    equipment_tag: str | None = None
    device_tag: str | None = None
    ts: datetime
    is_predictive: bool = False
    description: str | None = None


class AutoActionEvent(BaseModel):
    action_id: int | None = None
    action_type: str
    equipment_tag: str | None = None
    target_tag: str | None = None
    status: str
    level: int = 4
    rationale: str | None = None
    estimated_savings_usd: float = 0.0
    ts: datetime
