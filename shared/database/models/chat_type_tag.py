from sqlalchemy import Column, String, ForeignKey, DateTime, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from shared.database.session import Base


class ChatTypeTag(Base):
    __tablename__ = "chat_type_tags"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    chat_type_id = Column(Uuid(as_uuid=True), ForeignKey("chat_types.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    chat_type = relationship("ChatType", back_populates="tags")
    
    def __repr__(self):
        return f"<ChatTypeTag(id={self.id}, chat_type_id={self.chat_type_id}, tag='{self.tag}')>"
