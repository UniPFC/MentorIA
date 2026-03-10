from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from shared.database.session import Base


class ChatType(Base):
    __tablename__ = "chat_types"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True, nullable=False, index=True)
    owner_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    collection_name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="chat_types")
    chats = relationship("Chat", back_populates="chat_type", cascade="all, delete-orphan")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="chat_type", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatType(id={self.id}, name='{self.name}', is_public={self.is_public})>"
