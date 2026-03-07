"""Project model for organizing code context.

A project represents a codebase or workspace that has associated
conventions, files, and context that should be injected into prompts.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from api.models.api_key import Base


class Project(Base):
    """A project containing code context for prompt injection.

    Attributes:
        id: Primary key.
        name: Human-readable project name.
        description: Optional project description.
        conventions: Coding conventions and style guidelines to inject.
        system_prompt: Custom system prompt override for this project.
        api_key_id: Owner API key (multi-tenant isolation).
        created_at: Timestamp of creation.
        updated_at: Timestamp of last modification.
        files: Related ProjectFile records.
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    conventions = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    api_key = relationship("ApiKey", back_populates="projects")
