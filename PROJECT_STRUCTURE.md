# Project skeleton — Abadan Petrochemical CBM Smart Dashboard

> This document describes the repository (monorepo) structure and the implementation roadmap.
> The full description of the requirements is in [`README.md`](README.md) (the SRS document).

## Overview

```
inno-Abadan-Petrochemical-Smart-Dash/
├── README.md                     # SRS document and domain description (source of truth for requirements)
├── PROJECT_STRUCTURE.md           # this document
├── docker-compose.yml            # bring up the whole stack for local development
├── Makefile                      # common shortcuts (up, down, seed, lint, test)
├── .env.example                  # environment variable template
│
├── docs/                         # architecture and design documentation
│   ├── architecture.md           # ISO 13374 layers and data flow
│   ├── data-model.md             # asset hierarchy: complex→unit→line→equipment→sensor/camera
│   ├── auto-operation.md         # smart operator design (5 levels + on/off control)
│   ├── api.md                    # REST/WebSocket contract of the API gateway
│   └── standards.md              # mapping to ISO 17359 / 14224 / 13374 / IEC 62443
│
├── packages/
│   └── contracts/                # shared contracts between services and the frontend
│       ├── openapi/              # OpenAPI spec of each service
│       ├── asyncapi/            # AsyncAPI spec for Kafka/MQTT topics
│       └── schemas/             # JSON Schema of events (telemetry, alert, action)
│
├── apps/
│   └── dashboard/                # React + Vite + TypeScript frontend (RTL/Persian)
│       └── src/
│           ├── features/         # each dashboard page is an independent module
│           │   ├── overview/            # complex heat map (SRS 4-1)
│           │   ├── equipment/           # equipment details + FFT/Waterfall chart
│           │   ├── alerts/              # prioritized real-time alerts
│           │   ├── prediction/          # RUL and 7/30/90-day trends
│           │   ├── auto-operation/      # status and log of automatic actions + on/off control
│           │   ├── sensor-health/       # sensor health color codes (green/yellow/orange)
│           │   ├── acoustic/            # acoustic analysis and leak detection
│           │   └── reports/             # daily/weekly/monthly reports
│           ├── components/       # shared UI components (Gauge, HealthBadge, AssetTree ...)
│           ├── lib/api/          # REST + WebSocket client
│           ├── hooks/            # React hooks (useLiveTelemetry, useAssetTree ...)
│           ├── store/            # global state (Zustand)
│           ├── i18n/             # translations (fa default, en)
│           └── theme/            # light/dark theme + right-to-left direction
│
├── services/                     # backend microservices (Python / FastAPI) — NFR-17
│   ├── common/                   # shared library (config, logging, db, kafka, auth, domain models)
│   ├── api-gateway/              # BFF: authentication, RBAC, aggregation, WebSocket to the dashboard
│   ├── asset-registry/           # CRUD of the asset hierarchy and equipment↔sensor↔camera mapping
│   ├── data-acquisition/         # ingestion from MQTT/DCS/OPC-UA → Kafka (FR-01..05)
│   ├── signal-processing/        # FFT/Wavelet, noise filtering, feature extraction (FR-06,07)
│   ├── ai-engine/                # LSTM+CNN detection of 16 faults, acoustic spectral analysis (FR-08,09,10)
│   ├── prediction-rul/           # RUL estimation and 72-hour alerts (FR-11,12,13)
│   ├── sensor-health/            # monitoring 6 sensor health parameters and color coding (section 5)
│   ├── auto-operation/           # decision engine + start/stop/standby swap control (FR-14..17)
│   ├── alerting/                 # alert rules, prioritization, email/SMS/in-app notifications (FR-21)
│   └── reporting/                # automatic report generation and cost-benefit analysis (FR-19)
│
├── ml/                           # model lifecycle
│   ├── datagen/                  # synthetic data generators (SRS section 10)
│   │   ├── vibration.py          # vibration data + injection of 4 failure patterns
│   │   ├── acoustic.py           # acoustic data + leak events
│   │   ├── sensor_health.py      # green/yellow/orange status chain
│   │   ├── rul.py                # RUL labels
│   │   ├── auto_operation.py     # log of automatic actions
│   │   ├── process.py            # DCS process data
│   │   └── assets.py             # building the asset hierarchy and sensor/camera mapping
│   ├── features/                 # feature engineering pipeline shared with the signal-processing service
│   ├── models/                   # model architectures (fault_cnn_lstm, rul_estimator, acoustic_net)
│   ├── training/                 # training and evaluation scripts (Accuracy≥95%, FAR<5%)
│   └── notebooks/                # data exploration
│
├── data/
│   ├── raw/                      # ingested raw data (not version-controlled)
│   └── synthetic/                # output of the section 10 generators (not version-controlled)
│
├── infra/
│   ├── docker/                   # base Dockerfile and build scripts
│   ├── grafana/                  # dashboard and datasource provisioning
│   ├── mosquitto/                # MQTT broker configuration
│   ├── influxdb/                 # bucket setup script
│   ├── postgres/                 # initial schema migrations
│   └── k8s/                      # deployment manifests (helm/kustomize) — next phase
│
└── scripts/
    ├── seed_synthetic.py         # generate and load all synthetic data
    ├── bootstrap.sh              # install dependencies for all sub-projects
    └── check_standards.py        # check requirement↔code mapping coverage
```

## Mapping of architecture layers (README §2-1) to code

| README layer | Service/module |
|---|---|
| Data layer (Data Acquisition) | `services/data-acquisition`, `infra/mosquitto` |
| Processing layer (Edge/Cloud) | `services/signal-processing`, `ml/features` |
| Analysis layer (AI/ML Engine) | `services/ai-engine`, `services/prediction-rul`, `services/auto-operation`, `ml/models` |
| Presentation layer (Dashboard) | `apps/dashboard`, `services/api-gateway`, `infra/grafana` |

## Mapping of functional requirements to services

| FR code | Responsible service |
|---|---|
| FR-01 … FR-05 | `data-acquisition` |
| FR-06 … FR-10 | `signal-processing`, `ai-engine` |
| FR-11 … FR-13 | `prediction-rul` |
| FR-14 … FR-17 | `auto-operation` |
| FR-18 … FR-21 | `api-gateway`, `alerting`, `reporting`, `apps/dashboard` |

## Technology stack (README §2-2 software requirements)

- **Frontend:** React.js + Vite + TypeScript, Grafana panels embedded
- **Backend:** Python 3.11 + FastAPI, microservices architecture
- **Database:** InfluxDB (time-series) + PostgreSQL (relational)
- **Messaging:** Kafka (internal bus) + MQTT (edge)
- **AI:** PyTorch / TensorFlow
- **Security:** TLS 1.3, RBAC, 2FA, full logging (ISA/IEC 62443)

## Quick Start

```bash
cp .env.example .env
make up           # bring up infrastructure + services
make seed         # generate and load synthetic data (section 10)
make dashboard    # run the frontend in development mode (http://localhost:5173)
```

## Implementation status

This repository is currently a **skeleton**: the folder structure, contracts, infrastructure configuration,
and service entry points with function signatures and TODOs. Domain logic is gradually
completed in later phases. Each service has a `README.md` with its scope and "next steps".
