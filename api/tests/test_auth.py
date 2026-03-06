"""Tests for authentication service and API key management."""

import datetime
from unittest.mock import patch

from api.models.api_key import ApiKey
from api.models.usage_log import UsageLog
from api.services.auth import (
    check_rate_limit,
    create_api_key,
    generate_api_key,
    validate_api_key,
)


def test_generate_api_key_format():
    """Generated keys start with bridge- prefix."""
    key = generate_api_key()
    assert key.startswith("bridge-")
    assert len(key) > 10


def test_generate_api_key_uniqueness():
    """Each generated key is unique."""
    keys = {generate_api_key() for _ in range(100)}
    assert len(keys) == 100


def test_create_api_key(db_session):
    """Creating a key persists it to the database."""
    api_key = create_api_key(db_session, "test-key")
    assert api_key.name == "test-key"
    assert api_key.key.startswith("bridge-")
    assert api_key.is_admin is False
    assert api_key.is_active is True

    fetched = db_session.query(ApiKey).filter(ApiKey.id == api_key.id).first()
    assert fetched is not None
    assert fetched.key == api_key.key


def test_create_admin_api_key(db_session):
    """Creating an admin key sets is_admin=True."""
    api_key = create_api_key(db_session, "admin-key", is_admin=True)
    assert api_key.is_admin is True


def test_validate_api_key_success(db_session):
    """Valid active keys are returned and usage is tracked."""
    api_key = create_api_key(db_session, "valid-key")
    result = validate_api_key(db_session, api_key.key)
    assert result is not None
    assert result.id == api_key.id
    assert result.request_count == 1
    assert result.last_used_at is not None


def test_validate_api_key_invalid(db_session):
    """Invalid keys return None."""
    result = validate_api_key(db_session, "bridge-nonexistent")
    assert result is None


def test_validate_api_key_inactive(db_session):
    """Inactive keys return None."""
    api_key = create_api_key(db_session, "inactive-key")
    api_key.is_active = False
    db_session.commit()

    result = validate_api_key(db_session, api_key.key)
    assert result is None


def test_check_rate_limit_allowed(db_session):
    """Requests within limit are allowed."""
    api_key = create_api_key(db_session, "rate-test")
    assert check_rate_limit(db_session, api_key.id, 60) is True


def test_check_rate_limit_exceeded(db_session):
    """Requests exceeding limit are blocked."""
    api_key = create_api_key(db_session, "rate-test")
    now = datetime.datetime.utcnow()
    for _ in range(5):
        log = UsageLog(api_key_id=api_key.id, endpoint="/test", created_at=now)
        db_session.add(log)
    db_session.commit()

    assert check_rate_limit(db_session, api_key.id, 5) is False
    assert check_rate_limit(db_session, api_key.id, 6) is True
