"""Authentication service for API key validation and management."""

import datetime
import logging
import secrets

from sqlalchemy.orm import Session

from api.models.api_key import ApiKey

logger = logging.getLogger(__name__)


def generate_api_key() -> str:
    """Generate a new API key with the bridge- prefix.

    Returns:
        A unique API key string like 'bridge-abc123...'.
    """
    return f"bridge-{secrets.token_hex(24)}"


def create_api_key(db: Session, name: str, is_admin: bool = False) -> ApiKey:
    """Create and persist a new API key.

    Args:
        db: Database session.
        name: Human-readable name for the key.
        is_admin: Whether this key has admin privileges.

    Returns:
        The created ApiKey record.
    """
    key = generate_api_key()
    api_key = ApiKey(key=key, name=name, is_admin=is_admin)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    logger.info("Created API key '%s' (admin=%s)", name, is_admin)
    return api_key


def validate_api_key(db: Session, key: str) -> ApiKey | None:
    """Validate an API key and update its usage timestamp.

    Args:
        db: Database session.
        key: The API key string to validate.

    Returns:
        The ApiKey record if valid and active, None otherwise.
    """
    api_key = db.query(ApiKey).filter(ApiKey.key == key, ApiKey.is_active.is_(True)).first()
    if api_key:
        api_key.last_used_at = datetime.datetime.utcnow()
        api_key.request_count += 1
        db.commit()
        logger.debug("Validated key '%s' (count=%d)", api_key.name, api_key.request_count)
    return api_key


def check_rate_limit(db: Session, api_key_id: int, limit_per_minute: int) -> bool:
    """Check if an API key has exceeded its rate limit.

    Args:
        db: Database session.
        api_key_id: The ID of the API key to check.
        limit_per_minute: Maximum requests allowed per minute.

    Returns:
        True if the request is allowed, False if rate limited.
    """
    from api.models.usage_log import UsageLog

    one_minute_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    count = (
        db.query(UsageLog)
        .filter(UsageLog.api_key_id == api_key_id, UsageLog.created_at >= one_minute_ago)
        .count()
    )
    allowed = count < limit_per_minute
    if not allowed:
        logger.warning("Rate limit exceeded for key_id=%d (count=%d)", api_key_id, count)
    return allowed
