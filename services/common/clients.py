"""Shared HTTP client for inter-service calls (async, with retry)."""
from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from services.common.config import get_settings

_settings = get_settings()


class ServiceClient:
    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, max=3))
    async def get(self, path: str, **kw: Any) -> Any:
        r = await self._client.get(path, **kw)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, max=3))
    async def post(self, path: str, json: Any = None, **kw: Any) -> Any:
        r = await self._client.post(path, json=json, **kw)
        r.raise_for_status()
        return r.json()

    async def aclose(self) -> None:
        await self._client.aclose()


def asset_registry() -> ServiceClient:
    return ServiceClient(_settings.url_asset_registry)


def auto_operation() -> ServiceClient:
    return ServiceClient(_settings.url_auto_operation)


def economics() -> ServiceClient:
    return ServiceClient(_settings.url_economics)


def alerting() -> ServiceClient:
    return ServiceClient(_settings.url_alerting)


def reporting() -> ServiceClient:
    return ServiceClient(_settings.url_reporting)
