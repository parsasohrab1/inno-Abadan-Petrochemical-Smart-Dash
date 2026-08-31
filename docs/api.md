# قرارداد API — دروازه‌ی api-gateway (پورت ۸۰۰۰)

همه‌ی مسیرهای `/api/*` نیازمند هدر `Authorization: Bearer <token>` هستند
(در حالت `ENVIRONMENT=development` نقش پیش‌فرض manager فرض می‌شود).

## احراز هویت

| متد | مسیر | توضیح |
|---|---|---|
| POST | `/auth/login` | فرم `username`/`password` → `access_token` |
| GET | `/auth/me` | اطلاعات کاربر جاری |
| GET | `/auth/users` | فهرست کاربران (فقط admin) |

کاربران نمونه (seed خودکار): `admin/admin123`، `manager/manager123`، `engineer/engineer123`،
`operator/operator123`، `viewer/viewer123`.

## داشبرد

| متد | مسیر | خروجی |
|---|---|---|
| GET | `/api/overview` | شمارش تجهیز/سنسور/دوربین به تفکیک رنگ، هشدارها، واحدها |
| GET | `/api/heatmap` | آرایه‌ی تجهیزات با رنگ سلامت و مختصات واحد/خط |
| GET | `/api/equipment/{tag}` | جزئیات + آخرین تشخیص/RUL + روندها (۷/۳۰ روز) |
| GET | `/api/equipment/{tag}/spectrum` | دامنه در مضارب ۰٫۵X..۵X برای نمودار FFT |
| GET | `/api/alerts?active_only=true` | هشدارهای فعال |
| GET | `/api/predictions` | RUL همه‌ی تجهیزات، مرتب بر اساس فوریت |
| GET | `/api/sensor-health?color=red` | سه‌چراغ سنسور/دوربین + واحد اندازه‌گیری |
| GET | `/api/auto-operation/actions` `/stats` | اقدامات و آمار Auto Operation |
| POST | `/api/auto-operation/actions/{id}/approve\|reject` | تصمیم انسانی (operator) |
| POST | `/api/auto-operation/control/{tag}/start\|stop\|changeover` | کنترل مستقیم (operator) |
| GET | `/api/economics/live` | **سود و صرفه‌جویی لحظه‌ای به دلار** (کارت مدیریتی) |
| GET | `/api/economics/history?hours=24` | سری زمانی اقتصادی (manager) |
| GET | `/api/reports?kind=daily` | فهرست گزارش‌ها |
| WS | `/ws` | پخش زنده: کانال‌های `alert`, `auto_action`, `diagnosis`, `rul`, `economics` |

## سرویس‌های داخلی (بدون عبور از gateway)

| سرویس | پورت | نمونه مسیر |
|---|---|---|
| asset-registry | 8001 | `/equipment/{tag}/full`, `/coverage/unmonitored`, `/stats` |
| auto-operation | 8002 | `/actions/pending`, `/policy` |
| economics | 8003 | `/live`, `/breakdown`, `/pricebook` |
| alerting | 8004 | `/alerts/summary`, `/alerts/{id}/ack` |
| reporting | 8005 | `/reports/generate?kind=cost_benefit` |

## موضوعات Kafka (AsyncAPI در `packages/contracts/asyncapi`)

```
telemetry.vibration      → signal-processing
telemetry.acoustic       → ai-engine
telemetry.process        → economics (نرخ تولید), tsdb
telemetry.device_health  → sensor-health
analytics.features       → ai-engine
analytics.diagnosis      → prediction-rul, auto-operation
analytics.rul            → auto-operation
events.alerts            → alerting
events.alerts_inapp      → api-gateway (WebSocket)
events.auto_operation    → economics, api-gateway
```
