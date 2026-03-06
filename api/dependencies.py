"""FastAPI dependency injection for authentication."""

import logging

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.models.api_key import ApiKey
from api.services.auth import create_api_key, validate_api_key

logger = logging.getLogger(__name__)
security = HTTPBearer()


def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> ApiKey:
    """Extract and validate the API key from the Authorization header.

    Automatically bootstraps the admin key on first use if it matches
    the configured BRIDGE_ADMIN_API_KEY.

    Args:
        credentials: The Bearer token from the request header.
        db: Database session.

    Returns:
        The validated ApiKey record.

    Raises:
        HTTPException: 401 if the key is invalid or inactive.
    """
    key = credentials.credentials

    # Bootstrap: if the admin key is used and doesn't exist yet, create it
    if key == settings.admin_api_key:
        existing = db.query(ApiKey).filter(ApiKey.key == key).first()
        if not existing:
            logger.info("Bootstrapping admin API key")
            admin = ApiKey(key=key, name="admin", is_admin=True, is_active=True)
            db.add(admin)
            db.commit()
            db.refresh(admin)

    api_key = validate_api_key(db, key)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    return api_key
