"""بررسی پوشش نگاشت نیازمندی ↔ کد (ISO 17359 / 14224 / 13374, FR/NFR).

خروجی: جدول نیازمندی‌های SRS و ماژول متناظر. برای CI و مرور مهندسی.
"""
from __future__ import annotations

COVERAGE = {
    "FR-01..05 (Data Acquisition)": "services/data_acquisition",
    "FR-06,07 (FFT/Hann, features)": "ml/features/extract.py, services/signal_processing",
    "FR-08,09 (CNN+LSTM/GBM, 16 faults)": "ml/models/fault_classifier.py, services/common/domain/faults.py",
    "FR-10 (acoustic leak)": "ml/datagen/acoustic.py, services/ai_engine",
    "FR-11,12,13 (RUL, 72h lead, trends)": "services/prediction_rul, ml/models/rul_estimator.py",
    "FR-14..17 (Auto Operation + HITL)": "services/auto_operation",
    "FR-18 (live color dashboard)": "services/api_gateway, apps/dashboard",
    "FR-19 (auto reports)": "services/reporting",
    "FR-20 (history/trends)": "services/common/tsdb.py, api_gateway /api/equipment",
    "FR-21 (email/SMS/in-app)": "services/alerting/notifier.py",
    "Sensor 3-light health (§5)": "services/sensor_health, services/common/domain/health.py",
    "Manager profit/savings USD": "services/economics",
    "Asset↔sensor↔camera mapping": "services/asset_registry/seed.py, /coverage/unmonitored",
    "NFR-10..14 (TLS/2FA/RBAC/audit)": "services/common/security.py, AuditLog model",
    "NFR-17 (microservices)": "docker-compose.yml, services/*",
}

if __name__ == "__main__":
    width = max(len(k) for k in COVERAGE)
    for req, mod in COVERAGE.items():
        print(f"{req.ljust(width)}  ->  {mod}")
