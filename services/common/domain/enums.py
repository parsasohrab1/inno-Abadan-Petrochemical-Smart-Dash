"""Domain enumerations — per README §3, §4, §5, §6."""
from __future__ import annotations

from enum import Enum


class HealthColor(str, Enum):
    """Three-light performance monitoring of sensor/camera/equipment (README §5-1 + user requirement)."""

    GREEN = "green"   # healthy
    YELLOW = "yellow"  # warning / needs calibration
    RED = "red"        # fault / needs replacement  (README used the word "orange")


class SignalQuality(str, Enum):
    """Data quality per ISO 13374."""

    GOOD = "good"
    UNCERTAIN = "uncertain"
    BAD = "bad"


class SensorKind(str, Enum):
    ACCELEROMETER_TRIAX = "accelerometer_triax"
    VELOMETER = "velometer"
    PROXIMITY_PROBE = "proximity_probe"
    ULTRASONIC_MIC = "ultrasonic_mic"
    BROADBAND_ACOUSTIC = "broadband_acoustic"
    ACOUSTIC_EMISSION = "acoustic_emission"
    PRESSURE = "pressure"
    TEMPERATURE_RTD = "temperature_rtd"
    TEMPERATURE_TC = "temperature_tc"
    FLOW_METER = "flow_meter"
    LEVEL = "level"
    GAS_DETECTOR = "gas_detector"


class CameraKind(str, Enum):
    THERMAL = "thermal"
    AI_CCTV = "ai_cctv"
    HYPERSPECTRAL = "hyperspectral"


# default unit of measure of each sensor type (README §3) — shown next to the value in the dashboard
DEFAULT_UNIT: dict[str, str] = {
    SensorKind.ACCELEROMETER_TRIAX: "g",
    SensorKind.VELOMETER: "mm/s",
    SensorKind.PROXIMITY_PROBE: "µm",
    SensorKind.ULTRASONIC_MIC: "dB",
    SensorKind.BROADBAND_ACOUSTIC: "dB(A)",
    SensorKind.ACOUSTIC_EMISSION: "dB AE",
    SensorKind.PRESSURE: "bar",
    SensorKind.TEMPERATURE_RTD: "°C",
    SensorKind.TEMPERATURE_TC: "°C",
    SensorKind.FLOW_METER: "m³/h",
    SensorKind.LEVEL: "%",
    SensorKind.GAS_DETECTOR: "ppm",
    CameraKind.THERMAL: "°C",
    CameraKind.AI_CCTV: "event",
    CameraKind.HYPERSPECTRAL: "ppm·m",
}


class EquipmentType(str, Enum):
    PUMP = "pump"
    COMPRESSOR = "compressor"
    FAN = "fan"
    TURBINE = "turbine"
    MOTOR = "motor"
    REACTOR = "reactor"
    HEAT_EXCHANGER = "heat_exchanger"
    COLUMN = "column"
    VESSEL = "vessel"


class EquipmentRunState(str, Enum):
    """On/off state for Auto Operation control."""

    RUNNING = "running"
    STOPPED = "stopped"
    STANDBY = "standby"      # standby ready
    STARTING = "starting"
    STOPPING = "stopping"
    TRIPPED = "tripped"      # emergency stop
    MAINTENANCE = "maintenance"


class Criticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SAFETY_CRITICAL = "safety_critical"


class FaultType(str, Enum):
    """16 common faults of rotating equipment (FR-09)."""

    NORMAL = "normal"
    UNBALANCE = "unbalance"
    MISALIGNMENT = "misalignment"
    MECHANICAL_LOOSENESS = "mechanical_looseness"
    BEARING_INNER_RACE = "bearing_inner_race"
    BEARING_OUTER_RACE = "bearing_outer_race"
    BEARING_BALL = "bearing_ball"
    BEARING_CAGE = "bearing_cage"
    ROTOR_RUB = "rotor_rub"
    BENT_SHAFT = "bent_shaft"
    GEAR_MESH_WEAR = "gear_mesh_wear"
    BROKEN_ROTOR_BAR = "broken_rotor_bar"
    OIL_WHIRL = "oil_whirl"
    CAVITATION = "cavitation"
    RESONANCE = "resonance"
    BELT_DEFECT = "belt_defect"
    ELECTRICAL_STATOR = "electrical_stator"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    MAJOR = "major"
    CRITICAL = "critical"


class AutoActionType(str, Enum):
    """Automatic actions (README §6-3)."""

    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    LINE_SWITCH = "line_switch"          # switch to the backup line
    SPARE_CHANGEOVER = "spare_changeover"  # start the standby, shut down the main
    EQUIPMENT_START = "equipment_start"
    EQUIPMENT_STOP = "equipment_stop"
    MAINTENANCE_REQUEST = "maintenance_request"
    SPARE_PART_ORDER = "spare_part_order"
    MAINTENANCE_SCHEDULING = "maintenance_scheduling"
    ALERT_ESCALATION = "alert_escalation"
    REPORT_GENERATION = "report_generation"


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    AWAITING_APPROVAL = "awaiting_approval"  # FR-17 Human-in-the-loop
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"


class AutoOpMode(str, Enum):
    ADVISORY = "advisory"      # suggestion only
    SUPERVISED = "supervised"  # execution after human approval
    AUTONOMOUS = "autonomous"  # automatic execution except for safety-critical actions


class Role(str, Enum):
    """RBAC (NFR-12)."""

    VIEWER = "viewer"
    OPERATOR = "operator"
    MAINTENANCE = "maintenance"
    ENGINEER = "engineer"
    MANAGER = "manager"
    ADMIN = "admin"
