"""InfluxDB access layer for time series of vibration/acoustic/process/features."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from services.common.config import get_settings
from services.common.logging import get_logger

log = get_logger("common.tsdb")
_settings = get_settings()


class TimeSeriesDB:
    def __init__(self) -> None:
        self._client: InfluxDBClient | None = None

    @property
    def client(self) -> InfluxDBClient:
        if self._client is None:
            self._client = InfluxDBClient(
                url=_settings.influx_url,
                token=_settings.influx_token,
                org=_settings.influx_org,
            )
        return self._client

    def write_reading(
        self,
        measurement: str,
        tags: dict[str, str],
        fields: dict[str, float],
        ts: datetime | None = None,
    ) -> None:
        p = Point(measurement)
        for k, v in tags.items():
            p = p.tag(k, v)
        for k, v in fields.items():
            p = p.field(k, float(v))
        p = p.time(ts or datetime.now(timezone.utc))
        try:
            self.client.write_api(write_options=SYNCHRONOUS).write(
                bucket=_settings.influx_bucket, record=p
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("tsdb.write.failed", measurement=measurement, error=str(exc))

    def query_series(
        self,
        measurement: str,
        equipment_tag: str,
        field: str,
        lookback: timedelta = timedelta(hours=24),
        every: str = "5m",
    ) -> list[dict[str, Any]]:
        flux = f'''
        from(bucket: "{_settings.influx_bucket}")
          |> range(start: -{int(lookback.total_seconds())}s)
          |> filter(fn: (r) => r._measurement == "{measurement}")
          |> filter(fn: (r) => r.equipment_tag == "{equipment_tag}")
          |> filter(fn: (r) => r._field == "{field}")
          |> aggregateWindow(every: {every}, fn: mean, createEmpty: false)
          |> yield(name: "mean")
        '''
        try:
            tables = self.client.query_api().query(flux)
            return [
                {"ts": rec.get_time().isoformat(), "value": rec.get_value()}
                for table in tables
                for rec in table.records
            ]
        except Exception as exc:  # noqa: BLE001
            log.warning("tsdb.query.failed", error=str(exc))
            return []


tsdb = TimeSeriesDB()
