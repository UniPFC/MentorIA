from sqlalchemy import Column, ForeignKey, DateTime, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from shared.database.session import Base


class ChatTypeFavorite(Base):
    __tablename__ = "chat_type_favorites"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_type_id = Column(Uuid(as_uuid=True), ForeignKey("chat_types.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="favorite_chat_types")
    chat_type = relationship("ChatType", back_populates="favorited_by")
    
    # Ensure a user can only favorite a chat type once
    __table_args__ = (
        UniqueConstraint('user_id', 'chat_type_id', name='uq_user_chat_type_favorite'),
    )
    
    def __repr__(self):
        return f"<ChatTypeFavorite(user_id={self.user_id}, chat_type_id={self.chat_type_id})>"
