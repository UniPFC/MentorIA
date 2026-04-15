from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from shared.database.models.chat_type import ChatType
from shared.database.models.chat_type_tag import ChatTypeTag


class ChatTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, chat_type_id: UUID, load_owner: bool = False) -> Optional[ChatType]:
        query = self.db.query(ChatType)
        if load_owner:
            query = query.options(joinedload(ChatType.owner))
        return query.filter(ChatType.id == chat_type_id).first()

    def get_by_name(self, name: str) -> Optional[ChatType]:
        return self.db.query(ChatType).filter(ChatType.name == name).first()

    def create(self, chat_type: ChatType) -> ChatType:
        self.db.add(chat_type)
        self.db.commit()
        self.db.refresh(chat_type)
        return chat_type

    def delete(self, chat_type: ChatType) -> None:
        self.db.delete(chat_type)
        self.db.commit()

    def search(
        self,
        query: Optional[str] = None,
        is_public: Optional[bool] = None,
        owner_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ChatType], int]:
        """
        Search chat types with filters.
        Shows public chat types or user's own chat types.
        """
        db_query = self.db.query(ChatType).options(joinedload(ChatType.owner))
        
        # Security filter: Public OR Owned by user
        if user_id:
            db_query = db_query.filter(
                or_(
                    ChatType.is_public == True,
                    ChatType.owner_id == user_id
                )
            )
        
        # Text search in name and description
        if query:
            search_filter = or_(
                ChatType.name.ilike(f"%{query}%"),
                ChatType.description.ilike(f"%{query}%")
            )
            db_query = db_query.filter(search_filter)
        
        # Filter by public/private
        if is_public is not None:
            db_query = db_query.filter(ChatType.is_public == is_public)
        
        # Filter by owner
        if owner_id is not None:
            db_query = db_query.filter(ChatType.owner_id == owner_id)
        
        total = db_query.count()
        chat_types = db_query.offset(skip).limit(limit).all()
        
        return chat_types, total

    def list_user_available(
        self,
        user_id: UUID,
        favorited_ids: List[UUID],
        is_public: Optional[bool] = None,
        owner_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ChatType], int]:
        """
        List chat types available to user (Steam Workshop style).
        Shows chat types owned by user (public or private) OR favorited chat types.
        """
        db_query = self.db.query(ChatType).options(joinedload(ChatType.owner))
        
        # Filter: Owned by user (public or private) OR Favorited by user
        db_query = db_query.filter(
            or_(
                ChatType.owner_id == user_id,
                ChatType.id.in_(favorited_ids) if favorited_ids else False
            )
        )
        
        if is_public is not None:
            db_query = db_query.filter(ChatType.is_public == is_public)
        
        if owner_id is not None:
            db_query = db_query.filter(ChatType.owner_id == owner_id)
        
        total = db_query.count()
        chat_types = db_query.offset(skip).limit(limit).all()
        
        return chat_types, total

    def list_by_ids(
        self,
        chat_type_ids: List[UUID],
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ChatType], int]:
        """
        List chat types by IDs with pagination.
        """
        if not chat_type_ids:
            return [], 0
        
        db_query = self.db.query(ChatType).filter(
            ChatType.id.in_(chat_type_ids)
        ).options(joinedload(ChatType.owner))
        
        total = db_query.count()
        chat_types = db_query.offset(skip).limit(limit).all()
        
        return chat_types, total

    def add_tags(self, chat_type_id: UUID, tags: List[str]) -> None:
        """Add tags to a chat type, replacing existing tags."""
        # Delete existing tags
        self.db.query(ChatTypeTag).filter(ChatTypeTag.chat_type_id == chat_type_id).delete()
        
        # Add new tags
        for tag in tags:
            tag_obj = ChatTypeTag(chat_type_id=chat_type_id, tag=tag)
            self.db.add(tag_obj)
        
        self.db.commit()

    def get_tags(self, chat_type_id: UUID) -> List[str]:
        """Get all tags for a chat type."""
        tags = self.db.query(ChatTypeTag).filter(
            ChatTypeTag.chat_type_id == chat_type_id
        ).all()
        return [tag.tag for tag in tags]
