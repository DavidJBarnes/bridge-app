"""ProjectFile model for tracking files within a project.

Each file is split into chunks for efficient retrieval within
token budget constraints.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from api.models.api_key import Base


class ProjectFile(Base):
    """A file within a project, split into retrievable chunks.

    Attributes:
        id: Primary key.
        project_id: Parent project.
        file_path: Relative path within project (e.g., "src/UserService.java").
        file_type: Detected file type (java, typescript, python, etc.).
        summary: AI-generated or extracted summary of file purpose.
        total_tokens: Total token count of file content.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last modification.
        chunks: Related FileChunk records.
    """

    __tablename__ = "project_files"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    total_tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="files")
    chunks = relationship("FileChunk", back_populates="file", cascade="all, delete-orphan")
