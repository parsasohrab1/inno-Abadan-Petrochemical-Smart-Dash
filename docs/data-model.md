# Data model — asset hierarchy and sensor/camera monitoring

Source: README §1-3 (production units), §3 (inputs), §5 (sensor health), §8-1 (camera coverage).

## 1. Asset hierarchy (Asset Hierarchy)

Every equipment and every part of the production line **must** be connected to its related sensors and cameras
(user requirement). Tree structure:

```
Plant (Abadan Petrochemical)
└── Area / Unit            units 200.300, 400.500, 600.700, 800.900, 1000,
    │                       new PVC / tetramer / DDB units, chlor-alkali, tanks, pipelines
    └── ProductionLine     production line (e.g., PVC-A line)
        └── Equipment      pump, compressor, fan, turbine, reactor, exchanger, tower, tank
            ├── Component   DE/NDE bearing, shaft, impeller, coupling, driver motor
            ├── Sensor[]    ← many-to-many mapping via SensorMount
            └── Camera[]    ← many-to-many mapping via CameraCoverage
```

### PostgreSQL tables (`asset-registry`)

| Table | Key fields |
|---|---|
| `plant` | id, name, location, design_temp_c, humidity_range |
| `unit` | id, plant_id, code (`200-300` …), title, criticality |
| `production_line` | id, unit_id, code, title, product (`PVC`/`Caustic`/`DDB`) |
| `equipment` | id, line_id, tag (KKS/ISA), type, manufacturer, rpm_nominal, install_year, criticality, health_score |
| `component` | id, equipment_id, type, position (`DE`/`NDE`/`shaft` …) |
| `sensor` | id, tag, kind, unit_of_measure, range_min, range_max, sample_rate_hz, protocol, health_status |
| `camera` | id, tag, kind, resolution, fps, unit_of_measure, health_status |
| `sensor_mount` | sensor_id, equipment_id, component_id?, axis (`X`/`Y`/`Z`), measured_quantity |
| `camera_coverage` | camera_id, unit_id?, line_id?, equipment_id?, purpose |
| `maintenance_record` | id, equipment_id, date, action, parts_replaced, inspector (README §3-5) |

> The `sensor_mount` and `camera_coverage` mappings guarantee that from every node of the asset
> tree one can reach the related sensors/cameras and vice versa.

## 2. Sensor types and unit of measure (README §3)

The unit of measure of each sensor **must be displayed next to the value in the dashboard** (user requirement).

| `sensor.kind` | Quantity | `unit_of_measure` | Reference range | README source |
|---|---|---|---|---|
| `accelerometer_triax` | Vibration acceleration | `g` (or `m/s²`) | 0–50 kHz bandwidth | §3-1 |
| `velometer` | Vibration velocity | `mm/s` | 0–100 | §3-1 |
| `proximity_probe` | Shaft displacement | `µm` | 0–2000 | §3-1 |
| `ultrasonic_mic` | Ultrasonic sound level | `dB` | — | §3-2 |
| `broadband_acoustic` | Sound pressure | `dB(A)` | — | §3-2 |
| `acoustic_emission` | AE event | `dB AE` / `hits` | — | §3-2 |
| `pressure` | Pressure | `bar` (or `kPa`) | line/tank/reactor | §3-4 |
| `temperature_rtd` / `temperature_tc` | Temperature | `°C` | -5 to 55+ ambient | §3-4 |
| `flow_meter` | Flow | `m³/h` (or `t/h`) | feed/product | §3-4 |
| `level` | Level | `%` (or `mm`) | tanks/towers | §3-4 |
| `gas_detector` | Gas concentration | `ppm` (or `%LEL`) | flammable/toxic | §3-4 |

| `camera.kind` | Quantity | `unit_of_measure` |
|---|---|---|
| `thermal` | Surface temperature | `°C` |
| `ai_cctv` | Visual event (flame/smoke/leak) | `event` / `confidence %` |
| `hyperspectral` | Leaked gas concentration | `ppm·m` |

## 3. Sensor and camera performance monitoring — three lights

Each sensor and each camera is monitored with **three color states** (user requirement):

| Color | `health_status` | Meaning | Action |
|---|---|---|---|
| 🟢 Green | `green` | Healthy; valid data | Normal monitoring |
| 🟡 Yellow | `yellow` | Deviation/needs calibration | Check and calibrate |
| 🔴 Red | `red` | Faulty/invalid data | Repair or replace |

> Note: README §5-1 names the third color "orange"; per the user's request, red
> is used as the fault state. The mapping in `services/common/domain/health.py`
> is configurable (`FAULT_COLOR=red`).

### Health monitoring parameters (README §5-2) — `sensor-health` service

1. Supply voltage: `24V ± 5%`
2. Output signal: within `4–20 mA`
3. Signal quality: `SNR` (dB)
4. Measurement accuracy: deviation from reference
5. Communication: transmission rate and delay (ms)
6. Sensor operating temperature: within the allowed range

Color rule (default, configurable in `sensor_health_rules.yaml`):

```
red    if: disconnection > 60s  or  outside 4–20mA  or  voltage outside ±10%
yellow if: SNR < 20dB  or  calibration deviation > 2%  or  calibration > 90 days
green  otherwise
```

## 4. Telemetry event (JSON Schema — `packages/contracts/schemas`)

```jsonc
// telemetry.reading
{
  "sensor_tag": "P-1201-VIB-DE-X",
  "equipment_tag": "P-1201",
  "ts": "2026-08-28T10:15:03.250Z",
  "value": 3.7,
  "unit": "mm/s",           // always accompanies the value
  "quality": "good",         // good | uncertain | bad  (ISO 13374)
  "sensor_health": "green"
}
```

## 5. Equipment health index

`health_score ∈ [0,100]` (README §4-1). Weighted combination: severity of the diagnosed fault,
feature trends (RMS/Kurtosis), distance from ISO 10816 thresholds, and normalized RUL.
Equipment color: `green ≥ 75`, `yellow 45–75`, `red < 45` (configurable).
