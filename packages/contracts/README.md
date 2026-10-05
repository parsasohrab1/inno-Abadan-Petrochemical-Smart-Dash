# Shared contracts

The source of truth for the shape of data exchanged between services and the frontend.

- `schemas/` — JSON Schema of Kafka/MQTT events. Python equivalent: `services/common/schemas.py`.
- `openapi/` — OpenAPI spec of each service (extracted from the `/openapi.json` of each FastAPI service:
  `curl localhost:8001/openapi.json > openapi/asset-registry.json`).
- `asyncapi/` — description of the messaging topics (mapping in `docs/api.md`).

When changing an event: first the schema here, then `services/common/schemas.py`, then the producer/consumer.
