"""Database session management and table creation.

Uses SQLAlchemy create_all() for schema management in development (no Alembic).
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.config import settings
from api.models.api_key import Base
from api.models.usage_log import UsageLog  # noqa: F401 — register table
from api.models.project import Project  # noqa: F401 — register table
from api.models.project_file import ProjectFile  # noqa: F401 — register table
from api.models.file_chunk import FileChunk  # noqa: F401 — register table

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all database tables using SQLAlchemy metadata.

    Called at application startup. Safe to call multiple times.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")


def get_db():
    """Yield a database session for dependency injection.

    Yields:
        A SQLAlchemy Session that is automatically closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
