"""Tests for database initialization and session management."""

from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.models.api_key import Base


def test_create_all_creates_tables():
    """create_all() creates the expected tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "api_keys" in tables
    assert "usage_logs" in tables


def test_create_all_idempotent():
    """create_all() is safe to call multiple times."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "api_keys" in tables


def test_get_db_yields_and_closes():
    """get_db yields a session and closes it after use."""
    mock_session = MagicMock()
    mock_session_factory = MagicMock(return_value=mock_session)

    with patch("api.database.SessionLocal", mock_session_factory):
        from api.database import get_db

        gen = get_db()
        session = next(gen)
        assert session is mock_session

        # Exhaust the generator to trigger finally block
        try:
            next(gen)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()


def test_init_db():
    """init_db creates tables on the configured engine."""
    with patch("api.database.Base") as mock_base:
        from api.database import init_db

        init_db()
        mock_base.metadata.create_all.assert_called_once()
