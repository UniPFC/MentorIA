from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from shared.database.session import Base


class KnowledgeChunk(Base):
    """
    Metadata registry for knowledge chunks stored in Qdrant.
    The actual content (question, answer) and embeddings are stored in Qdrant collections.
    This table is used for tracking, auditing, and linking chunks to chat types.
    """
    __tablename__ = "knowledge_chunks"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    chat_type_id = Column(Uuid(as_uuid=True), ForeignKey("chat_types.id", ondelete="CASCADE"), nullable=False, index=True)
    qdrant_point_id = Column(String(100), nullable=False, index=True)
    source_file = Column(String(255), nullable=True)
    row_number = Column(Integer, nullable=True)
    chunk_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    chat_type = relationship("ChatType", back_populates="knowledge_chunks")
    
    def __repr__(self):
        return f"<KnowledgeChunk(id={self.id}, chat_type_id={self.chat_type_id}, qdrant_point_id='{self.qdrant_point_id}')>"
