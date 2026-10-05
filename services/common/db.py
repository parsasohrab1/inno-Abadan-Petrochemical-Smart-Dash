"""Connection to PostgreSQL via SQLModel/SQLAlchemy."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel

from services.common.config import get_settings
from services.common.logging import get_logger

log = get_logger("common.db")

_settings = get_settings()
engine = create_engine(_settings.postgres_dsn, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    """Create tables from the registered models (for development; use Alembic in production)."""
    import services.common.domain.models  # noqa: F401  register the models

    SQLModel.metadata.create_all(engine)
    log.info("db.schema.ready")


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with session_scope() as s:
        yield s
