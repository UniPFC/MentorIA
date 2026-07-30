import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import relationship

from shared.database.session import Base


class ChatType(Base):
    __tablename__ = "chat_types"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True, nullable=False, index=True)
    owner_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    collection_name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="chat_types")
    chats = relationship("Chat", back_populates="chat_type")
    knowledge_chunks = relationship(
        "KnowledgeChunk", back_populates="chat_type", cascade="all, delete-orphan"
    )
    favorited_by = relationship(
        "ChatTypeFavorite", back_populates="chat_type", cascade="all, delete-orphan"
    )
    tags = relationship(
        "ChatTypeTag", back_populates="chat_type", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<ChatType(id={self.id}, name='{self.name}', is_public={self.is_public})>"
        )
