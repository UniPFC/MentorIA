from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from shared.database.session import Base


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    chat_id = Column(Uuid(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat_id={self.chat_id}, role='{self.role.value}')>"
