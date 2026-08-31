# نگاشت به استانداردهای مرجع

| استاندارد | دامنه | جای پیاده‌سازی در پروژه |
|---|---|---|
| **ISO 17359** | راهنمای عمومی پایش وضعیت و عیب‌یابی | زنجیره‌ی `data-acquisition → signal-processing → ai-engine → prediction-rul`؛ چرخه‌ی هشدار/توصیه/اقدام در `auto-operation` |
| **ISO 13374** | پردازش داده‌ی پایش وضعیت (بلوک‌های DA/DM/SD/HA/PA/AG) | DA: `data_acquisition`؛ DM: `signal_processing/denoise.py` + `ml/features`؛ SD: `ai_engine`؛ HA: `prediction_rul` (health_score)؛ PA: `prediction_rul` (RUL)؛ AG: `auto_operation/engine.py` |
| **ISO 14224** | جمع‌آوری داده‌ی قابلیت‌اطمینان و نگهداری | مدل `Equipment/Component/MaintenanceRecord`؛ سلسله‌مراتب دارایی در `docs/data-model.md` |
| **ISO 10816 / 20816** | آستانه‌ی شدت ارتعاش تجهیز دوار | آستانه‌های رنگ در `services/common/domain/health.py` (قابل کالیبراسیون) |
| **ISA/IEC 62443** | امنیت سایبری سیستم‌های کنترل صنعتی | `services/common/security.py` (JWT، RBAC)، `AuditLog`، TLS در ingress، جداسازی شبکه‌ی سرویس‌ها |
| **IEC 60534 / NAMUR NE 107** | طبقه‌بندی وضعیت دستگاه میدانی (سه‌چراغ) | `HealthColor` و قواعد `evaluate_device_health` در `sensor_health` |

## نیازمندی‌های غیرعملکردی کلیدی (README §۴)

| کد | هدف | محل کنترل |
|---|---|---|
| NFR-01 | پاسخ داشبرد < ۲s | کش خواندنی gateway، ایندکس DB |
| NFR-02 | تأخیر end-to-end < ۵۰۰ms | پردازش جریانی Kafka بدون I/O دیسک در مسیر داغ |
| NFR-04 | ≥ ۱۰٬۰۰۰ داده/ثانیه | پارتیشن Kafka بر `equipment_tag`، مصرف‌کننده‌ی افقی |
| NFR-08 | دقت تشخیص ≥ ۹۵٪ | گیت CI در `ml/training/train_fault_model.py` |
| NFR-09 | نرخ هشدار اشتباه < ۵٪ | هموارسازی EMA شدت + آستانه‌ی رویداد در `ai_engine`؛ پایش در گزارش `ai_performance` |
| NFR-12 | RBAC | `require_role` در همه‌ی endpointهای نوشتنی |
| NFR-13 | لاگ کامل | `structlog` JSON + جدول `AuditLog` |
