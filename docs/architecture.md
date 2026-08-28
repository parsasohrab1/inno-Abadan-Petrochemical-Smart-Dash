# معماری سیستم — داشبرد هوشمند CBM پتروشیمی آبادان

منبع: README §۲ و §۹ (SRS). این سند نگاشت لایه‌های مفهومی به مؤلفه‌های اجرایی است.

## ۱. لایه‌ها (ISO 13374)

```
┌───────────────────────────── لایه نمایش ─────────────────────────────┐
│  apps/dashboard (React/Vite/TS, RTL)   ┆   Grafana (پنل‌های embed)     │
│        ▲ REST / WebSocket                                             │
│  services/api-gateway  ──  RBAC + 2FA + تجمیع + push لحظه‌ای            │
├──────────────────────────── لایه تحلیل (AI/ML) ──────────────────────┤
│  ai-engine (CNN+LSTM، ۱۶ عیب، تحلیل طیفی صوت)                          │
│  prediction-rul (RUL، هشدار ۷۲ساعته)                                  │
│  auto-operation (موتور تصمیم ۵ سطحی + کنترل روشن/خاموش/زاپاس)          │
│  sensor-health (پایش ۶ پارامتری، سه‌چراغ)                             │
├─────────────────────────── لایه پردازش (Edge/Cloud) ─────────────────┤
│  signal-processing (FFT/Wavelet، فیلتر نویز، Feature Extraction)      │
├─────────────────────────── لایه داده (Acquisition) ─────────────────┤
│  data-acquisition (MQTT / OPC-UA / DCS gateway)  →  Kafka             │
│  asset-registry (سلسله‌مراتب دارایی + نگاشت سنسور/دوربین)              │
└─────────────────────────────────────────────────────────────────────┘
        │                         │                        │
   InfluxDB (سری‌زمانی)      PostgreSQL (رابطه‌ای)      MinIO/S3 (تصاویر، مدل‌ها)
```

## ۲. جریان داده (Data Flow)

1. **دریافت:** سنسورهای لبه از طریق MQTT و DCS از طریق OPC-UA به `data-acquisition` می‌رسند.
   نرخ ارتعاش ≥ ۲۵.۶ kHz، صوت ≥ ۴۴.۱ kHz، فرآیند ≥ ۱ Hz (FR-01..04).
2. **باس رویداد:** `data-acquisition` رکوردهای خام را روی topicهای Kafka منتشر می‌کند
   (`telemetry.vibration/acoustic/process`). خام‌ها هم‌زمان در InfluxDB ذخیره می‌شوند.
3. **پردازش سیگنال:** `signal-processing` پنجره‌بندی Hann + FFT، فیلتر نویز، و ویژگی‌های
   آماری (RMS, Peak, Crest Factor, Kurtosis) را محاسبه و روی `analytics.features` منتشر می‌کند.
4. **تشخیص:** `ai-engine` روی ویژگی‌ها و طیف‌ها مدل CNN+LSTM را اجرا و نوع عیب + شدت را
   روی `analytics.diagnosis` منتشر می‌کند (Accuracy ≥ ۹۵٪).
5. **پیش‌بینی:** `prediction-rul` از روند عیب، RUL و زمان تخمینی خرابی را محاسبه و در صورت
   RUL < ۷۲h هشدار پیش‌بینی صادر می‌کند.
6. **سلامت سنسور:** `sensor-health` مستقل از مسیر بالا، شش پارامتر هر سنسور/دوربین را
   ارزیابی و وضعیت سه‌رنگ را نگه می‌دارد.
7. **تصمیم/اقدام:** `auto-operation` از diagnosis + RUL + محدودیت‌های فرآیندی، اقدام
   پیشنهادی (تنظیم پارامتر، تعویض به زاپاس، روشن/خاموش، درخواست تعمیر) را تولید و
   بسته به `AUTO_OP_MODE` اجرا یا برای تأیید انسانی صف می‌کند (FR-17).
8. **هشدار/گزارش:** `alerting` اعلان‌ها را از کانال‌های ایمیل/پیامک/این‌اپ می‌فرستد؛
   `reporting` گزارش‌های دوره‌ای و تحلیل هزینه-فایده تولید می‌کند.
9. **نمایش:** `api-gateway` وضعیت تجمیع‌شده را از PostgreSQL/InfluxDB می‌خواند و از طریق
   WebSocket به داشبرد push می‌کند (زمان پاسخ < ۲s، تأخیر end-to-end < ۵۰۰ms).

## ۳. ذخیره‌سازی

| داده | فناوری | مخزن |
|---|---|---|
| سری‌زمانی ارتعاش/صوت/فرآیند، ویژگی‌ها | InfluxDB | bucket `cbm_timeseries` |
| سلسله‌مراتب دارایی، سنسور/دوربین، نگاشت‌ها | PostgreSQL | `asset-registry` |
| هشدارها، work order، لاگ Auto Operation، audit | PostgreSQL | `alerting` / `auto-operation` |
| تصاویر حرارتی/CCTV، artifactهای مدل | Object store (MinIO/S3) | bucket `cbm-media`, `cbm-models` |

## ۴. مرزهای سرویس و ارتباط

- **همگام (REST):** فقط از `api-gateway` به سرویس‌های پایین‌دست برای پرس‌وجوهای on-demand.
- **ناهمگام (Kafka):** کل مسیر داغ تله‌متری → پردازش → تشخیص → اقدام.
- **قرارداد:** هر سرویس اسپک OpenAPI خود را در `packages/contracts/openapi/<service>.yaml`
  و رویدادهایش را در `packages/contracts/asyncapi` منتشر می‌کند.

## ۵. الزامات غیرعملکردی مرتبط با معماری

| کد | تصمیم معماری |
|---|---|
| NFR-02 (تأخیر < ۵۰۰ms) | پردازش جریانی؛ بدون ذخیره‌ی میانی روی دیسک در مسیر داغ |
| NFR-04 (۱۰٬۰۰۰ رکورد/ثانیه) | پارتیشن‌بندی Kafka بر اساس `equipment_tag`؛ مصرف‌کننده‌های افقی |
| NFR-05 / NFR-06 (RTO < ۱h، در دسترس‌بودن ≥ ۹۹.۹٪) | استقرار Active-Active سرور مرکزی، سرویس‌های stateless |
| NFR-15/16 (۲۰۰۰ سنسور، ۱۰۰۰ تجهیز) | asset-registry ایندکس‌گذاری‌شده؛ کش خواندنی در gateway |
| NFR-10..14 (امنیت) | TLS 1.3 در ingress، JWT + RBAC در gateway، audit log مرکزی |

## ۶. محیط توسعه‌ی محلی

`docker-compose.yml` این‌ها را بالا می‌آورد: postgres, influxdb, kafka+zookeeper,
mosquitto, grafana, minio و همه‌ی سرویس‌های `services/*`. فرانت‌اند جدا با
`make dashboard` اجرا می‌شود.
