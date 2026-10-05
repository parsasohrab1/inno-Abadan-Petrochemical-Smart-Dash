# API contract — api-gateway (port 8000)

All `/api/*` paths require the header `Authorization: Bearer <token>`
(in `ENVIRONMENT=development` the default role manager is assumed).

## Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | form `username`/`password` → `access_token` |
| GET | `/auth/me` | current user information |
| GET | `/auth/users` | list of users (admin only) |

Sample users (automatic seed): `admin/admin123`, `manager/manager123`, `engineer/engineer123`,
`operator/operator123`, `viewer/viewer123`.

## Dashboard

| Method | Path | Output |
|---|---|---|
| GET | `/api/overview` | equipment/sensor/camera counts by color, alerts, units |
| GET | `/api/heatmap` | array of equipment with health color and unit/line coordinates |
| GET | `/api/equipment/{tag}` | details + latest diagnosis/RUL + trends (7/30 days) |
| GET | `/api/equipment/{tag}/spectrum` | amplitude at multiples 0.5X..5X for the FFT chart |
| GET | `/api/alerts?active_only=true` | active alerts |
| GET | `/api/predictions` | RUL of all equipment, sorted by urgency |
| GET | `/api/sensor-health?color=red` | sensor/camera three-light + unit of measure |
| GET | `/api/auto-operation/actions` `/stats` | Auto Operation actions and statistics |
| POST | `/api/auto-operation/actions/{id}/approve\|reject` | human decision (operator) |
| POST | `/api/auto-operation/control/{tag}/start\|stop\|changeover` | direct control (operator) |
| GET | `/api/economics/live` | **instantaneous profit and savings in dollars** (management card) |
| GET | `/api/economics/history?hours=24` | economics time series (manager) |
| GET | `/api/reports?kind=daily` | list of reports |
| WS | `/ws` | live broadcast: channels `alert`, `auto_action`, `diagnosis`, `rul`, `economics` |

## Internal services (not passing through the gateway)

| Service | Port | Sample path |
|---|---|---|
| asset-registry | 8001 | `/equipment/{tag}/full`, `/coverage/unmonitored`, `/stats` |
| auto-operation | 8002 | `/actions/pending`, `/policy` |
| economics | 8003 | `/live`, `/breakdown`, `/pricebook` |
| alerting | 8004 | `/alerts/summary`, `/alerts/{id}/ack` |
| reporting | 8005 | `/reports/generate?kind=cost_benefit` |

## Kafka topics (AsyncAPI in `packages/contracts/asyncapi`)

```
telemetry.vibration      → signal-processing
telemetry.acoustic       → ai-engine
telemetry.process        → economics (production rate), tsdb
telemetry.device_health  → sensor-health
analytics.features       → ai-engine
analytics.diagnosis      → prediction-rul, auto-operation
analytics.rul            → auto-operation
events.alerts            → alerting
events.alerts_inapp      → api-gateway (WebSocket)
events.auto_operation    → economics, api-gateway
```
