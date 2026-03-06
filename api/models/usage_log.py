"""Usage log model for tracking API request history."""

import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from api.models.api_key import Base


class UsageLog(Base):
    """Tracks individual API requests for analytics and rate limiting."""

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key_id = Column(Integer, nullable=False)
    endpoint = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    status_code = Column(Integer, default=200)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
