# اسکلت پروژه — داشبرد هوشمند CBM پتروشیمی آبادان

> این سند ساختار مخزن (monorepo) و نقشه‌ی راه پیاده‌سازی را توصیف می‌کند.
> شرح کامل نیازمندی‌ها در [`README.md`](README.md) (سند SRS) آمده است.

## نمای کلی

```
inno-Abadan-Petrochemical-Smart-Dash/
├── README.md                     # سند SRS و شرح دامنه (منبع حقیقت نیازمندی‌ها)
├── PROJECT_STRUCTURE.md           # همین سند
├── docker-compose.yml            # بالا آوردن کل پشته برای توسعه‌ی محلی
├── Makefile                      # میان‌بُرهای رایج (up, down, seed, lint, test)
├── .env.example                  # الگوی متغیرهای محیطی
│
├── docs/                         # مستندات معماری و طراحی
│   ├── architecture.md           # لایه‌های ISO 13374 و جریان داده
│   ├── data-model.md             # سلسله‌مراتب دارایی‌ها: مجتمع→واحد→خط→تجهیز→سنسور/دوربین
│   ├── auto-operation.md         # طراحی اوپراتور هوشمند (۵ سطح + کنترل روشن/خاموش)
│   ├── api.md                    # قرارداد REST/WebSocket دروازه‌ی API
│   └── standards.md              # نگاشت به ISO 17359 / 14224 / 13374 / IEC 62443
│
├── packages/
│   └── contracts/                # قراردادهای مشترک بین سرویس‌ها و فرانت‌اند
│       ├── openapi/              # اسپک OpenAPI هر سرویس
│       ├── asyncapi/            # اسپک AsyncAPI برای موضوعات Kafka/MQTT
│       └── schemas/             # JSON Schema رویدادها (telemetry, alert, action)
│
├── apps/
│   └── dashboard/                # فرانت‌اند React + Vite + TypeScript (RTL/فارسی)
│       └── src/
│           ├── features/         # هر صفحه‌ی داشبرد یک ماژول مستقل
│           │   ├── overview/            # نقشه‌ی حرارتی مجتمع (۵-۱ SRS)
│           │   ├── equipment/           # جزئیات تجهیز + نمودار FFT/Waterfall
│           │   ├── alerts/              # هشدارهای لحظه‌ای اولویت‌بندی‌شده
│           │   ├── prediction/          # RUL و روند ۷/۳۰/۹۰ روزه
│           │   ├── auto-operation/      # وضعیت و لاگ اقدامات خودکار + کنترل روشن/خاموش
│           │   ├── sensor-health/       # کدهای رنگی سلامت سنسور (سبز/زرد/نارنجی)
│           │   ├── acoustic/            # تحلیل صوتی و تشخیص نشتی
│           │   └── reports/             # گزارش‌های روزانه/هفتگی/ماهانه
│           ├── components/       # اجزای UI مشترک (Gauge, HealthBadge, AssetTree ...)
│           ├── lib/api/          # کلاینت REST + WebSocket
│           ├── hooks/            # React hooks (useLiveTelemetry, useAssetTree ...)
│           ├── store/            # وضعیت سراسری (Zustand)
│           ├── i18n/             # ترجمه‌ها (fa پیش‌فرض، en)
│           └── theme/            # تم روشن/تیره + جهت راست‌به‌چپ
│
├── services/                     # میکروسرویس‌های بک‌اند (Python / FastAPI) — NFR-17
│   ├── common/                   # کتابخانه‌ی مشترک (config, logging, db, kafka, auth, مدل‌های دامنه)
│   ├── api-gateway/              # BFF: احراز هویت، RBAC، تجمیع، WebSocket به داشبرد
│   ├── asset-registry/           # CRUD سلسله‌مراتب دارایی و نگاشت تجهیز↔سنسور↔دوربین
│   ├── data-acquisition/         # دریافت از MQTT/DCS/OPC-UA → Kafka (FR-01..05)
│   ├── signal-processing/        # FFT/Wavelet، فیلتر نویز، استخراج ویژگی (FR-06,07)
│   ├── ai-engine/                # LSTM+CNN تشخیص ۱۶ عیب، تحلیل طیفی صوت (FR-08,09,10)
│   ├── prediction-rul/           # تخمین RUL و هشدار ۷۲ ساعته (FR-11,12,13)
│   ├── sensor-health/            # پایش ۶ پارامتر سلامت سنسور و رنگ‌بندی (بخش ۵)
│   ├── auto-operation/           # موتور تصمیم + کنترل راه‌اندازی/توقف/تعویض زاپاس (FR-14..17)
│   ├── alerting/                 # قواعد هشدار، اولویت‌بندی، اعلان ایمیل/پیامک/این‌اپ (FR-21)
│   └── reporting/                # تولید خودکار گزارش و تحلیل هزینه-فایده (FR-19)
│
├── ml/                           # چرخه‌ی حیات مدل‌ها
│   ├── datagen/                  # مولّدهای داده‌ی سنتتیک (بخش ۱۰ SRS)
│   │   ├── vibration.py          # داده‌ی ارتعاش + تزریق ۴ الگوی خرابی
│   │   ├── acoustic.py           # داده‌ی صوتی + رویداد نشتی
│   │   ├── sensor_health.py      # زنجیره‌ی وضعیت سبز/زرد/نارنجی
│   │   ├── rul.py                # برچسب‌های RUL
│   │   ├── auto_operation.py     # لاگ اقدامات خودکار
│   │   ├── process.py            # داده‌ی فرآیندی DCS
│   │   └── assets.py             # ساخت سلسله‌مراتب دارایی و نگاشت سنسور/دوربین
│   ├── features/                 # پایپ‌لاین مهندسی ویژگی مشترک با سرویس signal-processing
│   ├── models/                   # معماری مدل‌ها (fault_cnn_lstm، rul_estimator، acoustic_net)
│   ├── training/                 # اسکریپت‌های آموزش و ارزیابی (Accuracy≥۹۵٪، FAR<۵٪)
│   └── notebooks/                # اکتشاف داده
│
├── data/
│   ├── raw/                      # داده‌ی خام واردشده (نسخه‌کنترل نمی‌شود)
│   └── synthetic/                # خروجی مولّدهای بخش ۱۰ (نسخه‌کنترل نمی‌شود)
│
├── infra/
│   ├── docker/                   # Dockerfile پایه و اسکریپت‌های build
│   ├── grafana/                  # provisioning داشبورد و datasource
│   ├── mosquitto/                # پیکربندی بروکر MQTT
│   ├── influxdb/                 # اسکریپت راه‌اندازی bucket
│   ├── postgres/                 # مهاجرت‌های اولیه‌ی اسکیما
│   └── k8s/                      # مانيفست‌های استقرار (helm/kustomize) — فاز بعد
│
└── scripts/
    ├── seed_synthetic.py         # تولید و بارگذاری کل داده‌ی سنتتیک
    ├── bootstrap.sh              # نصب وابستگی‌ها برای همه‌ی زیرپروژه‌ها
    └── check_standards.py        # بررسی پوشش نگاشت نیازمندی↔کد
```

## نگاشت لایه‌های معماری (README §۲-۱) به کد

| لایه README | سرویس/ماژول |
|---|---|
| لایه داده (Data Acquisition) | `services/data-acquisition`, `infra/mosquitto` |
| لایه پردازش (Edge/Cloud) | `services/signal-processing`, `ml/features` |
| لایه تحلیل (AI/ML Engine) | `services/ai-engine`, `services/prediction-rul`, `services/auto-operation`, `ml/models` |
| لایه نمایش (Dashboard) | `apps/dashboard`, `services/api-gateway`, `infra/grafana` |

## نگاشت نیازمندی‌های عملکردی به سرویس

| کد FR | سرویس مسئول |
|---|---|
| FR-01 … FR-05 | `data-acquisition` |
| FR-06 … FR-10 | `signal-processing`, `ai-engine` |
| FR-11 … FR-13 | `prediction-rul` |
| FR-14 … FR-17 | `auto-operation` |
| FR-18 … FR-21 | `api-gateway`, `alerting`, `reporting`, `apps/dashboard` |

## پشته‌ی فناوری (README §۲-۲ نیازمندی‌های نرم‌افزاری)

- **فرانت‌اند:** React.js + Vite + TypeScript، پنل‌های Grafana به‌صورت embed
- **بک‌اند:** Python 3.11 + FastAPI، معماری microservices
- **پایگاه داده:** InfluxDB (سری‌زمانی) + PostgreSQL (رابطه‌ای)
- **پیام‌رسانی:** Kafka (باس داخلی) + MQTT (لبه)
- **AI:** PyTorch / TensorFlow
- **امنیت:** TLS 1.3، RBAC، 2FA، لاگ‌گذاری کامل (ISA/IEC 62443)

## راه‌اندازی سریع

```bash
cp .env.example .env
make up           # بالا آوردن زیرساخت + سرویس‌ها
make seed         # تولید و بارگذاری داده‌ی سنتتیک (بخش ۱۰)
make dashboard    # اجرای فرانت‌اند در حالت توسعه (http://localhost:5173)
```

## وضعیت پیاده‌سازی

این مخزن در حال حاضر **اسکلت** است: ساختار پوشه‌ها، قراردادها، پیکربندی زیرساخت،
و نقاط ورود سرویس‌ها با امضای توابع و TODO مشخص. منطق دامنه به‌تدریج در فازهای بعد
تکمیل می‌شود. هر سرویس یک `README.md` با محدوده و «مراحل بعدی» دارد.
