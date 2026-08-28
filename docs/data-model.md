# مدل داده — سلسله‌مراتب دارایی و پایش سنسور/دوربین

منبع: README §۱-۳ (واحدهای تولیدی)، §۳ (ورودی‌ها)، §۵ (سلامت سنسورها)، §۸-۱ (پوشش دوربین).

## ۱. سلسله‌مراتب دارایی (Asset Hierarchy)

هر تجهیز و هر بخش از خط تولید **باید** به سنسورها و دوربین‌های مرتبط خود متصل باشد
(الزام کاربر). ساختار درختی:

```
Plant (پتروشیمی آبادان)
└── Area / Unit            واحدهای ۲۰۰.۳۰۰، ۴۰۰.۵۰۰، ۶۰۰.۷۰۰، ۸۰۰.۹۰۰، ۱۰۰۰،
    │                       واحدهای جدید PVC / تترامر / DDB، کلرآلکالی، مخازن، خطوط لوله
    └── ProductionLine     خط تولید (مثلاً خط PVC-A)
        └── Equipment      پمپ، کمپرسور، فن، توربین، راکتور، مبدل، برج، مخزن
            ├── Component   یاتاقان DE/NDE، شفت، ایمپلر، کوپلینگ، موتور محرک
            ├── Sensor[]    ← نگاشت چند‌به‌چند از طریق SensorMount
            └── Camera[]    ← نگاشت چند‌به‌چند از طریق CameraCoverage
```

### جدول‌های PostgreSQL (`asset-registry`)

| جدول | فیلدهای کلیدی |
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
| `maintenance_record` | id, equipment_id, date, action, parts_replaced, inspector (README §۳-۵) |

> نگاشت‌های `sensor_mount` و `camera_coverage` تضمین می‌کنند که از هر گره‌ی درخت
> دارایی می‌توان به سنسورها/دوربین‌های مرتبط رسید و برعکس.

## ۲. انواع سنسور و واحد اندازه‌گیری (README §۳)

واحد اندازه‌گیری هر سنسور **باید در داشبرد کنار مقدار نمایش داده شود** (الزام کاربر).

| `sensor.kind` | کمیت | `unit_of_measure` | محدوده‌ی مرجع | منبع README |
|---|---|---|---|---|
| `accelerometer_triax` | شتاب ارتعاش | `g` (یا `m/s²`) | ۰–۵۰ kHz پهنای‌باند | §۳-۱ |
| `velometer` | سرعت ارتعاش | `mm/s` | ۰–۱۰۰ | §۳-۱ |
| `proximity_probe` | جابه‌جایی شفت | `µm` | ۰–۲۰۰۰ | §۳-۱ |
| `ultrasonic_mic` | تراز صوت فراصوت | `dB` | — | §۳-۲ |
| `broadband_acoustic` | فشار صوت | `dB(A)` | — | §۳-۲ |
| `acoustic_emission` | رویداد AE | `dB AE` / `hits` | — | §۳-۲ |
| `pressure` | فشار | `bar` (یا `kPa`) | خط/مخزن/راکتور | §۳-۴ |
| `temperature_rtd` / `temperature_tc` | دما | `°C` | ۵− الی ۵۵+ محیط | §۳-۴ |
| `flow_meter` | دبی | `m³/h` (یا `t/h`) | خوراک/محصول | §۳-۴ |
| `level` | سطح | `%` (یا `mm`) | مخازن/برج‌ها | §۳-۴ |
| `gas_detector` | غلظت گاز | `ppm` (یا `%LEL`) | قابل‌اشتعال/سمی | §۳-۴ |

| `camera.kind` | کمیت | `unit_of_measure` |
|---|---|---|
| `thermal` | دمای سطح | `°C` |
| `ai_cctv` | رخداد بصری (شعله/دود/نشت) | `event` / `confidence %` |
| `hyperspectral` | غلظت گاز نشتی | `ppm·m` |

## ۳. پایش عملکرد سنسور و دوربین — سه چراغ

هر سنسور و هر دوربین با **سه وضعیت رنگی** پایش می‌شود (الزام کاربر):

| رنگ | `health_status` | معنی | اقدام |
|---|---|---|---|
| 🟢 سبز | `green` | سالم؛ داده‌ی معتبر | پایش عادی |
| 🟡 زرد | `yellow` | انحراف/نیاز به کالیبراسیون | بررسی و کالیبراسیون |
| 🔴 قرمز | `red` | خراب/داده‌ی نامعتبر | تعمیر یا تعویض |

> یادداشت: README §۵-۱ رنگ سوم را «نارنجی» نامیده است؛ طبق درخواست کاربر رنگ قرمز
> به‌عنوان وضعیت خطا استفاده می‌شود. نگاشت در `services/common/domain/health.py`
> قابل پیکربندی است (`FAULT_COLOR=red`).

### پارامترهای پایش سلامت (README §۵-۲) — سرویس `sensor-health`

۱. ولتاژ تغذیه: `24V ± 5%`
۲. سیگنال خروجی: در محدوده‌ی `4–20 mA`
۳. کیفیت سیگنال: `SNR` (dB)
۴. دقت اندازه‌گیری: انحراف از مرجع
۵. ارتباطات: نرخ ارسال و تأخیر (ms)
۶. دمای عملیاتی سنسور: در محدوده‌ی مجاز

قانون رنگ (پیش‌فرض، قابل تنظیم در `sensor_health_rules.yaml`):

```
red    اگر: قطع ارتباط > 60s  یا  خارج از 4–20mA  یا  ولتاژ خارج از ±10%
yellow اگر: SNR < 20dB  یا  انحراف کالیبراسیون > 2%  یا  کالیبراسیون > 90 روز
green  در غیر این صورت
```

## ۴. رویداد تله‌متری (JSON Schema — `packages/contracts/schemas`)

```jsonc
// telemetry.reading
{
  "sensor_tag": "P-1201-VIB-DE-X",
  "equipment_tag": "P-1201",
  "ts": "2026-08-28T10:15:03.250Z",
  "value": 3.7,
  "unit": "mm/s",           // همیشه همراه مقدار
  "quality": "good",         // good | uncertain | bad  (ISO 13374)
  "sensor_health": "green"
}
```

## ۵. شاخص سلامت تجهیز

`health_score ∈ [0,100]` (README §۴-۱). ترکیب وزنی: شدت عیب تشخیص‌داده‌شده،
روند ویژگی‌ها (RMS/Kurtosis)، فاصله تا آستانه‌های ISO 10816، و RUL نرمال‌شده.
رنگ تجهیز: `green ≥ 75`، `yellow 45–75`، `red < 45` (قابل تنظیم).
