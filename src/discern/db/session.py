"""SQLAlchemy engine + session factory, configured from Settings."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from discern.config import settings


def _make_engine(url: str):
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


_engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_session_factory(url: str):
    """Return a new (engine, SessionLocal) pair for the given URL (useful in tests)."""
    engine = _make_engine(url)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, factory


def get_default_engine():
    return _engine
