"""مدل‌های پایگاه‌داده (SQLModel) — سلسله‌مراتب دارایی و رکوردهای عملیاتی.

سلسله‌مراتب: Plant → Unit → ProductionLine → Equipment → Component
هر Equipment و ProductionLine از طریق SensorMount / CameraCoverage به سنسور و دوربین متصل است
(الزام کاربر: «تمامی تجهیزات و خط تولید زیر سنسور و دوربین مرتبط باشند»).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel

from services.common.domain.enums import (
    ActionStatus,
    AlertSeverity,
    AutoActionType,
    CameraKind,
    Criticality,
    EquipmentRunState,
    EquipmentType,
    FaultType,
    HealthColor,
    SensorKind,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- assets
class Plant(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = "پتروشیمی آبادان"
    location: str = "کوی مطهری، آبادان"
    design_temp_c: float = 49.0
    abs_max_temp_c: float = 55.0
    min_temp_c: float = -5.0
    humidity_min_pct: float = 4.0
    humidity_max_pct: float = 100.0
    units: list["Unit"] = Relationship(back_populates="plant")


class Unit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    plant_id: int = Field(foreign_key="plant.id", index=True)
    code: str = Field(index=True)          # "200-300", "400-500", "PVC-NEW", "CA" ...
    title: str
    criticality: Criticality = Criticality.MEDIUM
    plant: Plant | None = Relationship(back_populates="units")
    lines: list["ProductionLine"] = Relationship(back_populates="unit")


class ProductionLine(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id", index=True)
    code: str = Field(index=True)
    title: str
    product: str | None = None            # PVC | Caustic | DDB | Tetramer | EDC | VCM
    design_rate_tph: float | None = None  # ظرفیت طراحی (تن بر ساعت)
    unit: Unit | None = Relationship(back_populates="lines")
    equipment: list["Equipment"] = Relationship(back_populates="line")
    camera_coverages: list["CameraCoverage"] = Relationship(back_populates="line")


class Equipment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    line_id: int = Field(foreign_key="productionline.id", index=True)
    tag: str = Field(index=True, unique=True)   # نشانه‌ی KKS/ISA مثل P-1201
    name: str
    etype: EquipmentType
    manufacturer: str | None = None
    install_year: int | None = None
    rpm_nominal: float | None = None
    rated_power_kw: float | None = None
    criticality: Criticality = Criticality.MEDIUM
    has_spare: bool = False
    spare_of_id: int | None = Field(default=None, foreign_key="equipment.id")
    run_state: EquipmentRunState = EquipmentRunState.RUNNING
    health_score: float = 100.0
    health_color: HealthColor = HealthColor.GREEN
    line: ProductionLine | None = Relationship(back_populates="equipment")
    components: list["Component"] = Relationship(back_populates="equipment")
    sensor_mounts: list["SensorMount"] = Relationship(back_populates="equipment")
    camera_coverages: list["CameraCoverage"] = Relationship(back_populates="equipment")


class Component(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id", index=True)
    ctype: str                            # bearing | shaft | impeller | coupling | motor | gearbox
    position: str | None = None           # DE | NDE | inboard | outboard
    equipment: Equipment | None = Relationship(back_populates="components")


# --------------------------------------------------------------------------- sensing devices
class Sensor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tag: str = Field(index=True, unique=True)
    kind: SensorKind
    unit_of_measure: str                  # واحد اندازه‌گیری — همیشه در داشبرد نمایش داده می‌شود
    range_min: float = 0.0
    range_max: float = 100.0
    sample_rate_hz: float = 1.0
    protocol: str = "MQTT"                # MQTT | OPC-UA | 4-20mA | HART
    supply_voltage_nominal: float = 24.0
    installed_at: datetime | None = None
    last_calibration: datetime | None = None
    health_status: HealthColor = HealthColor.GREEN
    mounts: list["SensorMount"] = Relationship(back_populates="sensor")


class Camera(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tag: str = Field(index=True, unique=True)
    kind: CameraKind
    unit_of_measure: str = "°C"
    resolution: str = "640x480"
    fps: float = 9.0
    health_status: HealthColor = HealthColor.GREEN
    last_calibration: datetime | None = None
    coverages: list["CameraCoverage"] = Relationship(back_populates="camera")


class SensorMount(SQLModel, table=True):
    """نگاشت سنسور ↔ تجهیز/جزء (چند‌به‌چند).

    اگر سنسور در سطح واحد/خط باشد (گازسنج، فلومتر خط) `equipment_id` خالی است و
    `unit_id`/`line_id` مقدار می‌گیرد.
    """

    id: int | None = Field(default=None, primary_key=True)
    sensor_id: int = Field(foreign_key="sensor.id", index=True)
    equipment_id: int | None = Field(default=None, foreign_key="equipment.id", index=True)
    unit_id: int | None = Field(default=None, foreign_key="unit.id")
    line_id: int | None = Field(default=None, foreign_key="productionline.id")
    component_id: int | None = Field(default=None, foreign_key="component.id")
    axis: str | None = None               # X | Y | Z
    measured_quantity: str | None = None  # vibration_velocity | shaft_displacement | ...
    sensor: Sensor | None = Relationship(back_populates="mounts")
    equipment: Equipment | None = Relationship(back_populates="sensor_mounts")


class CameraCoverage(SQLModel, table=True):
    """نگاشت دوربین ↔ واحد/خط/تجهیز."""

    id: int | None = Field(default=None, primary_key=True)
    camera_id: int = Field(foreign_key="camera.id", index=True)
    unit_id: int | None = Field(default=None, foreign_key="unit.id")
    line_id: int | None = Field(default=None, foreign_key="productionline.id")
    equipment_id: int | None = Field(default=None, foreign_key="equipment.id", index=True)
    purpose: str = "general"              # leak | flame | smoke | thermal | intrusion
    camera: Camera | None = Relationship(back_populates="coverages")
    line: ProductionLine | None = Relationship(back_populates="camera_coverages")
    equipment: Equipment | None = Relationship(back_populates="camera_coverages")


# --------------------------------------------------------------------------- operational records
class MaintenanceRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id", index=True)
    performed_at: datetime = Field(default_factory=_now)
    action: str
    parts_replaced: str | None = None
    inspector: str | None = None
    cost_usd: float = 0.0
    downtime_hours: float = 0.0
    source_action_id: int | None = None   # اگر از Auto Operation آمده باشد


class DeviceHealthSnapshot(SQLModel, table=True):
    """آخرین ارزیابی ۶ پارامتری سلامت سنسور/دوربین (README §۵-۲)."""

    id: int | None = Field(default=None, primary_key=True)
    device_tag: str = Field(index=True)
    device_type: str = "sensor"           # sensor | camera
    ts: datetime = Field(default_factory=_now, index=True)
    status: HealthColor = HealthColor.GREEN
    supply_voltage: float | None = None
    loop_current_ma: float | None = None
    snr_db: float | None = None
    calibration_drift_pct: float | None = None
    comm_latency_ms: float | None = None
    device_temp_c: float | None = None
    reasons: str | None = None            # توضیح علت رنگ


class Diagnosis(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    equipment_tag: str = Field(index=True)
    ts: datetime = Field(default_factory=_now, index=True)
    fault_type: FaultType = FaultType.NORMAL
    severity: float = 0.0                 # ۰..۱
    confidence: float = 0.0               # ۰..۱
    features_json: str | None = None
    model_version: str = "v0"


class RulEstimate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    equipment_tag: str = Field(index=True)
    ts: datetime = Field(default_factory=_now, index=True)
    predicted_rul_hours: float = 0.0
    confidence: float = 0.0
    predicted_failure_at: datetime | None = None
    health_score: float = 100.0


class Alert(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_now, index=True)
    equipment_tag: str | None = Field(default=None, index=True)
    device_tag: str | None = None
    severity: AlertSeverity = AlertSeverity.WARNING
    code: str
    title: str
    description: str | None = None
    is_predictive: bool = False
    predicted_failure_at: datetime | None = None
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class AutoAction(SQLModel, table=True):
    """اقدام Auto Operation (README §۶) — شامل روشن/خاموش و تعویض زاپاس."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_now, index=True)
    action_type: AutoActionType
    equipment_tag: str | None = Field(default=None, index=True)
    target_tag: str | None = None         # تجهیز زاپاس/مقصد در صورت تعویض
    status: ActionStatus = ActionStatus.PROPOSED
    level: int = 4                        # سطح ۱..۵ (README §۶-۲)
    rationale: str | None = None
    parameters_json: str | None = None
    requires_human_approval: bool = True
    approved_by: str | None = None
    decided_at: datetime | None = None
    executed_at: datetime | None = None
    result_json: str | None = None
    estimated_savings_usd: float = 0.0
    diagnosis_id: int | None = Field(default=None, foreign_key="diagnosis.id")


class EquipmentStateChange(SQLModel, table=True):
    """تاریخچه‌ی تغییر وضعیت روشن/خاموش تجهیز."""

    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=_now, index=True)
    equipment_tag: str = Field(index=True)
    from_state: EquipmentRunState
    to_state: EquipmentRunState
    triggered_by: str = "auto-operation"  # auto-operation | operator:<name> | protection
    action_id: int | None = Field(default=None, foreign_key="autoaction.id")
    note: str | None = None


class EconomicsSnapshot(SQLModel, table=True):
    """عکس لحظه‌ای سود و صرفه‌جویی به دلار برای داشبرد مدیریتی (الزام کاربر)."""

    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=_now, index=True)
    profit_rate_usd_per_hour: float = 0.0
    savings_rate_usd_per_hour: float = 0.0
    profit_today_usd: float = 0.0
    savings_today_usd: float = 0.0
    savings_mtd_usd: float = 0.0
    breakdown_json: str | None = None


class Report(SQLModel, table=True):
    """گزارش تحلیلی تولیدشده (FR-19) — روزانه/هفتگی/ماهانه/هزینه-فایده."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_now, index=True)
    kind: str = Field(index=True)          # daily | weekly | monthly | cost_benefit | ai_performance
    period_start: datetime
    period_end: datetime
    title: str
    summary: str | None = None
    payload_json: str | None = None       # داده‌ی کامل گزارش
    format: str = "json"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    full_name: str | None = None
    hashed_password: str
    role: str = "viewer"
    totp_secret: str | None = None        # 2FA (NFR-11)
    is_active: bool = True


class AuditLog(SQLModel, table=True):
    """ثبت کامل فعالیت کاربر (NFR-13)."""

    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=_now, index=True)
    actor: str
    action: str
    target: str | None = None
    detail_json: str | None = None
    ip: str | None = None
