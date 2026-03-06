"""API key management endpoints (admin only)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.database import get_db
from api.dependencies import get_current_api_key
from api.models.api_key import ApiKey
from api.services.auth import create_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["keys"])


class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_admin: bool = False


class KeyResponse(BaseModel):
    key: str
    name: str
    is_admin: bool


@router.post("/keys", response_model=KeyResponse)
async def create_key(
    request: CreateKeyRequest,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a new API key (admin only).

    Only API keys with admin privileges can create new keys.
    """
    if not api_key.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    new_key = create_api_key(db, request.name, request.is_admin)
    logger.info("Admin '%s' created key '%s'", api_key.name, request.name)
    return KeyResponse(key=new_key.key, name=new_key.name, is_admin=new_key.is_admin)
