"""Database engine and the per-request session.

The application connects as the **restricted** role (`database_url`), never as
the owner. That is not a detail: ADR-0004 makes the audit trail append-only with
privileges plus a trigger, and an owner can undo both. `database_url_admin`
exists for Alembic and is deliberately not reachable from here.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_sessao_factory: sessionmaker[Session] | None = None


def engine() -> Engine:
    """The process-wide engine, built on first use."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            # An on-premise deployment restarts its database for maintenance;
            # without this the first request after each restart fails.
            pool_pre_ping=True,
        )
    return _engine


def sessao_factory() -> sessionmaker[Session]:
    """The process-wide session factory, built on first use."""
    global _sessao_factory
    if _sessao_factory is None:
        _sessao_factory = sessionmaker(bind=engine(), expire_on_commit=False)
    return _sessao_factory


def get_sessao() -> Iterator[Session]:
    """FastAPI dependency: one session, one transaction, per request.

    The commit is here rather than in each service because the audit row and the
    mutation it describes must land together — a service that commits on its own
    would be able to leave one without the other.
    """
    with sessao_factory()() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def reset_engine() -> None:
    """Drop the cached engine. Tests point the app at their own database."""
    global _engine, _sessao_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _sessao_factory = None
