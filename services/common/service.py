"""کارخانه‌ی ساخت اپلیکیشن FastAPI با تنظیمات مشترک (CORS، health، لاگ)."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.common.config import get_settings
from services.common.logging import configure_logging, get_logger


def create_app(
    title: str,
    *,
    version: str = "0.1.0",
    on_startup: Callable | None = None,
    on_shutdown: Callable | None = None,
) -> FastAPI:
    configure_logging()
    settings = get_settings()
    log = get_logger(title)

    app = FastAPI(title=title, version=version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "service": title, "version": version, "env": settings.environment}

    @app.on_event("startup")
    async def _startup() -> None:  # noqa: D401
        log.info("service.startup", service=title)
        if on_startup:
            await on_startup()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        log.info("service.shutdown", service=title)
        if on_shutdown:
            await on_shutdown()

    return app
