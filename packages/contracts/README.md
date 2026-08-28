# قراردادهای مشترک (Contracts)

منبع حقیقت برای شکل داده‌ی مبادله‌شده بین سرویس‌ها و فرانت‌اند.

- `schemas/` — JSON Schema رویدادهای Kafka/MQTT. معادل پایتونی: `services/common/schemas.py`.
- `openapi/` — اسپک OpenAPI هر سرویس (از `/openapi.json` هر سرویس FastAPI استخراج می‌شود:
  `curl localhost:8001/openapi.json > openapi/asset-registry.json`).
- `asyncapi/` — توصیف موضوعات پیام‌رسانی (نگاشت در `docs/api.md`).

هنگام تغییر یک رویداد: ابتدا schema اینجا، سپس `services/common/schemas.py`، سپس تولیدکننده/مصرف‌کننده.
