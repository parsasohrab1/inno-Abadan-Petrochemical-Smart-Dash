# System architecture — Abadan Petrochemical CBM Smart Dashboard

Source: README §2 and §9 (SRS). This document maps the conceptual layers to the executable components.

## 1. Layers (ISO 13374)

```
┌───────────────────────────── Presentation layer ─────────────────────┐
│  apps/dashboard (React/Vite/TS, RTL)   ┆   Grafana (embedded panels)  │
│        ▲ REST / WebSocket                                             │
│  services/api-gateway  ──  RBAC + 2FA + aggregation + real-time push   │
├──────────────────────────── Analysis layer (AI/ML) ──────────────────┤
│  ai-engine (CNN+LSTM, 16 faults, acoustic spectral analysis)           │
│  prediction-rul (RUL, 72-hour alert)                                  │
│  auto-operation (5-level decision engine + on/off/standby control)     │
│  sensor-health (6-parameter monitoring, three-light)                  │
├─────────────────────────── Processing layer (Edge/Cloud) ────────────┤
│  signal-processing (FFT/Wavelet, noise filter, Feature Extraction)    │
├─────────────────────────── Data layer (Acquisition) ─────────────────┤
│  data-acquisition (MQTT / OPC-UA / DCS gateway)  →  Kafka             │
│  asset-registry (asset hierarchy + sensor/camera mapping)              │
└─────────────────────────────────────────────────────────────────────┘
        │                         │                        │
   InfluxDB (time series)      PostgreSQL (relational)      MinIO/S3 (images, models)
```

## 2. Data flow

1. **Ingestion:** Edge sensors reach `data-acquisition` via MQTT and the DCS via OPC-UA.
   Vibration rate ≥ 25.6 kHz, acoustic ≥ 44.1 kHz, process ≥ 1 Hz (FR-01..04).
2. **Event bus:** `data-acquisition` publishes raw records on Kafka topics
   (`telemetry.vibration/acoustic/process`). Raw data is simultaneously stored in InfluxDB.
3. **Signal processing:** `signal-processing` performs Hann windowing + FFT, noise filtering, and computes statistical
   features (RMS, Peak, Crest Factor, Kurtosis) and publishes them on `analytics.features`.
4. **Diagnosis:** `ai-engine` runs the CNN+LSTM model on features and spectra and publishes the fault type + severity
   on `analytics.diagnosis` (Accuracy ≥ 95%).
5. **Prediction:** `prediction-rul` computes RUL and estimated failure time from the fault trend and issues a predictive alert if
   RUL < 72h.
6. **Sensor health:** `sensor-health`, independently of the path above, evaluates the six parameters of each sensor/camera
   and maintains the three-color status.
7. **Decision/action:** `auto-operation` produces the proposed action (parameter adjustment, switch to standby, on/off, maintenance request) from
   diagnosis + RUL + process constraints and, depending on
   `AUTO_OP_MODE`, executes it or queues it for human approval (FR-17).
8. **Alert/report:** `alerting` sends notifications through email/SMS/in-app channels;
   `reporting` generates periodic reports and the cost-benefit analysis.
9. **Presentation:** `api-gateway` reads the aggregated status from PostgreSQL/InfluxDB and pushes it to the dashboard via
   WebSocket (response time < 2s, end-to-end delay < 500ms).

## 3. Storage

| Data | Technology | Store |
|---|---|---|
| Time series of vibration/acoustic/process, features | InfluxDB | bucket `cbm_timeseries` |
| Asset hierarchy, sensor/camera, mappings | PostgreSQL | `asset-registry` |
| Alerts, work orders, Auto Operation log, audit | PostgreSQL | `alerting` / `auto-operation` |
| Thermal/CCTV images, model artifacts | Object store (MinIO/S3) | bucket `cbm-media`, `cbm-models` |

## 4. Service boundaries and communication

- **Synchronous (REST):** only from `api-gateway` to downstream services for on-demand queries.
- **Asynchronous (Kafka):** the entire hot path telemetry → processing → diagnosis → action.
- **Contract:** each service publishes its OpenAPI spec in `packages/contracts/openapi/<service>.yaml`
  and its events in `packages/contracts/asyncapi`.

## 5. Non-functional requirements related to architecture

| Code | Architecture decision |
|---|---|
| NFR-02 (delay < 500ms) | Stream processing; no intermediate disk storage on the hot path |
| NFR-04 (10,000 records/second) | Kafka partitioning by `equipment_tag`; horizontal consumers |
| NFR-05 / NFR-06 (RTO < 1h, availability ≥ 99.9%) | Active-Active deployment of the central server, stateless services |
| NFR-15/16 (2000 sensors, 1000 equipment) | Indexed asset-registry; read cache in the gateway |
| NFR-10..14 (security) | TLS 1.3 at ingress, JWT + RBAC in the gateway, central audit log |

## 6. Local development environment

`docker-compose.yml` brings up: postgres, influxdb, kafka+zookeeper,
mosquitto, grafana, minio and all `services/*` services. The frontend is run separately with
`make dashboard`.
