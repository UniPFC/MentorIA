"""
Service for managing chat sessions and messages.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Dict
from shared.database.models.message import Message, MessageRole
from config.logger import logger


class ChatService:
    """Service for chat operations."""

    def __init__(self, db: Session):
        self.db = db

    def save_message(self, chat_id: UUID, role: MessageRole, content: str) -> Message:
        """
        Save a message to the database.
        
        Args:
            chat_id: ID of the chat
            role: Message role (user or assistant)
            content: Message content
            
        Returns:
            Created Message object
        """
        try:
            message_created_at = datetime.now(timezone.utc)
            latest_created_at = self.db.query(Message.created_at).filter(
                Message.chat_id == chat_id
            ).order_by(Message.created_at.desc()).limit(1).scalar()

            if latest_created_at is not None:
                if latest_created_at.tzinfo is None:
                    latest_created_at = latest_created_at.replace(tzinfo=timezone.utc)
                if message_created_at <= latest_created_at:
                    message_created_at = latest_created_at + timedelta(microseconds=1)

            message = Message(
                chat_id=chat_id,
                role=role,
                content=content,
                created_at=message_created_at,
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            self.db.rollback()
            raise

    def get_chat_history(self, chat_id: UUID, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get recent chat history formatted for LLM context.
        Excludes the last user message to avoid including the current query in the history.
        
        Args:
            chat_id: ID of the chat
            limit: Number of messages to retrieve (before excluding current user message)
            
        Returns:
            List of message dicts [{"role": "...", "content": "..."}] excluding current user message
        """
        # Get limit + 1 messages to check if we need to exclude the last one
        all_messages = self.db.query(Message).filter(
            Message.chat_id == chat_id
        ).order_by(Message.created_at.desc()).limit(limit + 1).all()
        
        if not all_messages:
            return []
        
        # Skip the first message (most recent) if it's from the user (current query)
        messages_to_include = all_messages
        if all_messages[0].role == MessageRole.USER:
            messages_to_include = all_messages[1:]
        
        # Reverse to get chronological order (oldest to newest)
        messages_to_include = list(reversed(messages_to_include))
        
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages_to_include
        ]
