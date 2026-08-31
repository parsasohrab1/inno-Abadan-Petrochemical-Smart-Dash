"""پیکربندی مرکزی — از متغیرهای محیطی (.env) خوانده می‌شود."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # general
    project_name: str = "abadan-cbm"
    environment: str = "development"
    tz: str = "Asia/Tehran"
    log_level: str = "INFO"

    # gateway / auth
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    gateway_cors_origins: str = "http://localhost:5173"
    jwt_secret: str = "change-me-in-production"
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 30
    enable_2fa: bool = True

    # postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "abadan_cbm"
    postgres_user: str = "cbm"
    postgres_password: str = "cbm-dev-password"

    # influx
    influx_url: str = "http://localhost:8086"
    influx_org: str = "abadan"
    influx_bucket: str = "cbm_timeseries"
    influx_token: str = "dev-influx-token"

    # kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_vibration: str = "telemetry.vibration"
    kafka_topic_acoustic: str = "telemetry.acoustic"
    kafka_topic_process: str = "telemetry.process"
    kafka_topic_features: str = "analytics.features"
    kafka_topic_diagnosis: str = "analytics.diagnosis"
    kafka_topic_alerts: str = "events.alerts"
    kafka_topic_auto_ops: str = "events.auto_operation"

    # mqtt
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_base_topic: str = "abadan/edge"

    # ml / ai
    model_registry_path: str = "./ml/models/artifacts"
    rul_alert_lead_time_hours: int = 72
    fault_detection_min_accuracy: float = 0.95

    # auto operation
    auto_op_mode: str = "advisory"  # advisory | supervised | autonomous
    auto_op_require_human_approval: bool = True
    auto_op_max_autonomous_actions_per_hour: int = 20

    # service discovery (internal URLs)
    url_asset_registry: str = "http://localhost:8001"
    url_auto_operation: str = "http://localhost:8002"
    url_economics: str = "http://localhost:8003"
    url_alerting: str = "http://localhost:8004"
    url_reporting: str = "http://localhost:8005"

    # grafana
    grafana_url: str = "http://localhost:3000"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.gateway_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
