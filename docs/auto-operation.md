# طراحی اوپراتور هوشمند (Auto Operation)

منبع: README §۶ و FR-14..17. الهام‌گرفته از Honeywell Experion Cognition و ABB Ability Genix
(پیاده‌سازی Borouge).

## ۱. سطوح پنج‌گانه (README §۶-۲)

| سطح | نام | مؤلفه |
|---|---|---|
| ۱ پایش | مانیتورینگ ۲۴/۷ | `data-acquisition`, `sensor-health` |
| ۲ تحلیل | تشخیص الگوی خرابی > ۹۵٪ | `signal-processing`, `ai-engine` |
| ۳ هشدار | هشدار اولویت‌بندی‌شده | `prediction-rul`, `alerting` |
| ۴ توصیه | پیشنهاد اقدام اصلاحی | `auto-operation/engine.py` (کاهش بار، زمان‌بندی تعمیر، سفارش قطعه) |
| ۵ اقدام | اجرای خودکار | `auto-operation/control.py` (روشن/خاموش، تعویض زاپاس) |

## ۲. بهینه‌سازی برخط و کنترل روشن/خاموش (الزام کاربر)

سیستم قابلیت **خاموش‌کردن خودکار تجهیز (پمپ/کمپرسور/فن)** و **روشن‌کردن زاپاس** آن را دارد.

### درخت تصمیم برای هر تجهیز

```
شدت عیب < ۰٫۲۵  ────────────────► فقط پایش
۰٫۲۵ ≤ شدت < ۰٫۵۵ و RUL > ۷۲h ──► سطح ۴: کاهش ۱۵٪ بار + زمان‌بندی تعمیر + سفارش قطعه
شدت ≥ ۰٫۶  یا  RUL ≤ ۷۲h ───────► سطح ۵:
        ├─ دارای زاپاس؟ ──► SPARE_CHANGEOVER: استارت زاپاس، سپس توقف اصلی، انتقال به تعمیر
        ├─ ایمنی‌بحرانی و RUL ≤ ۲۴h و بدون زاپاس ──► EQUIPMENT_STOP (کنترل‌شده/اضطراری)
        └─ در غیر این صورت ──► درخواست تعمیر با اولویت بالا + کاهش ۳۰٪ بار
```

### تحلیل هزینه-فایده‌ی لحظه‌ای

اقدام تعویض/توقف تنها زمانی پیشنهاد می‌شود که:

```
صرفه‌جویی برآوردی = هزینه‌ی توقف اجتناب‌شده + هزینه‌ی خرابی فاجعه‌بار اجتناب‌شده
                  (از services/common/economics.py با قیمت‌نامه‌ی config/economics.yaml)
```

مقدار `estimated_savings_usd` هر اقدام به سرویس `economics` تغذیه می‌شود و در نرخ
«صرفه‌جویی لحظه‌ای» داشبورد مدیریتی ظاهر می‌شود.

## ۳. ماشین حالت تجهیز (`control.py`)

```
RUNNING ──stop──► STOPPING ──► STOPPED ──start──► STARTING ──► RUNNING
   │                                    │
   └──trip──► TRIPPED                    └──► STANDBY (زاپاس آماده)  /  MAINTENANCE
```

هر انتقال در جدول `equipmentstatechange` با `triggered_by` (auto-operation / operator:<name> /
protection) ثبت می‌شود. در محیط واقعی `_send_command` به OPC-UA writeback روی DCS/SIS متصل می‌شود.

## ۴. Human-in-the-loop (FR-17)

| حالت (`AUTO_OP_MODE`) | رفتار |
|---|---|
| `advisory` | همه‌ی اقدامات فقط «پیشنهاد» — هیچ اجرای خودکاری |
| `supervised` | اقدامات روشن/خاموش/تعویض نیازمند تأیید اپراتور؛ بقیه خودکار |
| `autonomous` | اجرای خودکار به‌جز تجهیزات ایمنی‌بحرانی (همیشه تأیید انسانی) |

`AUTO_OP_REQUIRE_HUMAN_APPROVAL=true` (پیش‌فرض) به‌صورت سراسری تأیید انسانی را برای
اقدامات کنترلی الزامی می‌کند. سقف `AUTO_OP_MAX_AUTONOMOUS_ACTIONS_PER_HOUR` از طوفان
اقدام جلوگیری می‌کند.

## ۵. API

| متد | مسیر | نقش لازم |
|---|---|---|
| GET | `/actions`, `/actions/pending`, `/actions/{id}` | viewer |
| POST | `/actions/{id}/approve` \| `/reject` | operator |
| POST | `/control/{tag}/start` \| `/stop` \| `/changeover` | operator |
| GET | `/equipment/{tag}/state` | viewer |
| GET/PATCH | `/policy` | engineer (برای PATCH) |
