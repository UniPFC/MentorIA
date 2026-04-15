from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from shared.database.models.chat_type_favorite import ChatTypeFavorite


class ChatTypeFavoriteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_and_chat_type(self, user_id: UUID, chat_type_id: UUID) -> Optional[ChatTypeFavorite]:
        return self.db.query(ChatTypeFavorite).filter(
            ChatTypeFavorite.user_id == user_id,
            ChatTypeFavorite.chat_type_id == chat_type_id
        ).first()

    def get_user_favorites(self, user_id: UUID) -> List[ChatTypeFavorite]:
        return self.db.query(ChatTypeFavorite).filter(
            ChatTypeFavorite.user_id == user_id
        ).all()

    def get_user_favorite_ids(self, user_id: UUID) -> List[UUID]:
        favorites = self.db.query(ChatTypeFavorite.chat_type_id).filter(
            ChatTypeFavorite.user_id == user_id
        ).all()
        return [fav[0] for fav in favorites]

    def create(self, user_id: UUID, chat_type_id: UUID) -> ChatTypeFavorite:
        favorite = ChatTypeFavorite(
            user_id=user_id,
            chat_type_id=chat_type_id
        )
        self.db.add(favorite)
        self.db.commit()
        self.db.refresh(favorite)
        return favorite

    def delete(self, favorite: ChatTypeFavorite) -> None:
        self.db.delete(favorite)
        self.db.commit()

    def delete_by_user_and_chat_type(self, user_id: UUID, chat_type_id: UUID) -> bool:
        favorite = self.get_by_user_and_chat_type(user_id, chat_type_id)
        if favorite:
            self.delete(favorite)
            return True
        return False

    def is_favorited(self, user_id: UUID, chat_type_id: UUID) -> bool:
        return self.get_by_user_and_chat_type(user_id, chat_type_id) is not None
