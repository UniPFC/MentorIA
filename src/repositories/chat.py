from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from shared.database.models.chat import Chat


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, chat_id: UUID) -> Optional[Chat]:
        return self.db.query(Chat).filter(Chat.id == chat_id).first()

    def get_by_user(
        self,
        user_id: UUID,
        chat_type_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Chat]:
        query = self.db.query(Chat).filter(Chat.user_id == user_id)
        
        if chat_type_id is not None:
            query = query.filter(Chat.chat_type_id == chat_type_id)
        
        return query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit).all()

    def count_by_user(self, user_id: UUID) -> int:
        return self.db.query(Chat).filter(Chat.user_id == user_id).count()

    def create(self, chat: Chat) -> Chat:
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        return chat

    def update(self, chat: Chat) -> Chat:
        self.db.commit()
        self.db.refresh(chat)
        return chat

    def delete(self, chat: Chat) -> None:
        self.db.delete(chat)
        self.db.commit()
