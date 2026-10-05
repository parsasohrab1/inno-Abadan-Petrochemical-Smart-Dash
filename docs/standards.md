# Mapping to reference standards

| Standard | Scope | Implementation location in the project |
|---|---|---|
| **ISO 17359** | General guide to condition monitoring and diagnostics | the chain `data-acquisition → signal-processing → ai-engine → prediction-rul`; alert/recommendation/action cycle in `auto-operation` |
| **ISO 13374** | Condition monitoring data processing (DA/DM/SD/HA/PA/AG blocks) | DA: `data_acquisition`; DM: `signal_processing/denoise.py` + `ml/features`; SD: `ai_engine`; HA: `prediction_rul` (health_score); PA: `prediction_rul` (RUL); AG: `auto_operation/engine.py` |
| **ISO 14224** | Reliability and maintenance data collection | `Equipment/Component/MaintenanceRecord` model; asset hierarchy in `docs/data-model.md` |
| **ISO 10816 / 20816** | Vibration severity thresholds of rotating equipment | color thresholds in `services/common/domain/health.py` (calibratable) |
| **ISA/IEC 62443** | Cybersecurity of industrial control systems | `services/common/security.py` (JWT, RBAC), `AuditLog`, TLS at ingress, network segregation of services |
| **IEC 60534 / NAMUR NE 107** | Field device status classification (three lights) | `HealthColor` and the `evaluate_device_health` rules in `sensor_health` |

## Key non-functional requirements (README §4)

| Code | Goal | Control location |
|---|---|---|
| NFR-01 | Dashboard response < 2s | gateway read cache, DB index |
| NFR-02 | End-to-end delay < 500ms | Kafka stream processing without disk I/O on the hot path |
| NFR-04 | ≥ 10,000 data points/second | Kafka partition on `equipment_tag`, horizontal consumer |
| NFR-08 | Detection accuracy ≥ 95% | CI gate in `ml/training/train_fault_model.py` |
| NFR-09 | False alarm rate < 5% | EMA severity smoothing + event threshold in `ai_engine`; monitoring in the `ai_performance` report |
| NFR-12 | RBAC | `require_role` on all write endpoints |
| NFR-13 | Full logging | `structlog` JSON + `AuditLog` table |
