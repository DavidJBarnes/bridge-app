"""Shared test fixtures for API tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import get_db
from api.main import app
from api.models.api_key import ApiKey, Base
from api.models.usage_log import UsageLog  # noqa: F401 — ensures table is registered


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine for testing with a shared connection."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Provide a database session bound to the test engine."""
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Provide a FastAPI test client with overridden database dependency."""

    def override_get_db():
        """Yield the test database session."""
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_key(db_session):
    """Create and return an admin API key for testing."""
    key = ApiKey(key="bridge-test-admin", name="test-admin", is_admin=True, is_active=True)
    db_session.add(key)
    db_session.commit()
    db_session.refresh(key)
    return key


@pytest.fixture
def user_key(db_session):
    """Create and return a regular user API key for testing."""
    key = ApiKey(key="bridge-test-user", name="test-user", is_admin=False, is_active=True)
    db_session.add(key)
    db_session.commit()
    db_session.refresh(key)
    return key


@pytest.fixture
def admin_headers(admin_key):
    """Provide authorization headers for admin API key."""
    return {"Authorization": f"Bearer {admin_key.key}"}


@pytest.fixture
def user_headers(user_key):
    """Provide authorization headers for regular user API key."""
    return {"Authorization": f"Bearer {user_key.key}"}
