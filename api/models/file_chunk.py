"""FileChunk model for storing retrievable code segments.

Chunks are the atomic unit of context retrieval. Each chunk represents
a logical unit of code (function, class, or fixed-size segment).
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from sqlalchemy.orm import relationship

from api.models.api_key import Base


class FileChunk(Base):
    """A retrievable segment of a project file.

    Attributes:
        id: Primary key.
        file_id: Parent file.
        chunk_index: Order within the file (0-based).
        chunk_type: Type of chunk (function, class, module, segment).
        signature: Function/class signature for TF-IDF boosting.
        content: The actual code content.
        token_count: Token count of this chunk.
        start_line: Starting line number in original file.
        end_line: Ending line number in original file.
        created_at: Timestamp of creation.
    """

    __tablename__ = "file_chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("project_files.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(50), default="segment")
    signature = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    start_line = Column(Integer, nullable=True)
    end_line = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    file = relationship("ProjectFile", back_populates="chunks")
