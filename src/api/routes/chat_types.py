"""
ChatType endpoints for managing chat types.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional
from uuid import UUID
from shared.database.session import get_db
from shared.database.models.chat_type import ChatType
from shared.database.models.chat_type_favorite import ChatTypeFavorite
from src.api.schemas.chat_type import (
    ChatTypeCreate,
    ChatTypeUpdate,
    ChatTypeResponse,
    ChatTypeListResponse,
    ChatTypeSearchParams,
    ChatTypeFavoriteResponse
)
from src.api.dependencies import (
    get_current_active_user,
    get_chat_type_repo,
    get_chat_type_favorite_repo
)
from src.repositories.chat_type import ChatTypeRepository
from src.repositories.chat_type_favorite import ChatTypeFavoriteRepository
from shared.database.models.user import User
from shared.qdrant.client import QdrantManager
from config.logger import logger

router = APIRouter(prefix="/chat-types", tags=["chat-types"])


def enrich_chat_type_with_owner(chat_type: ChatType, favorite_repo: ChatTypeFavoriteRepository = None, user_id: UUID = None) -> dict:
    """
    Helper function to add owner_name, is_favorited, and tags to ChatType response.
    Returns dict compatible with ChatTypeResponse schema.
    Chat types owned by user 'MentorIA' are system chat types.
    """
    # Get owner username from loaded relationship
    owner_name = chat_type.owner.username if chat_type.owner else None
    
    # Check if user has favorited this chat type
    is_favorited = False
    if favorite_repo and user_id:
        is_favorited = favorite_repo.is_favorited(user_id, chat_type.id)
    
    # Get tags from relationship
    tags = [tag.tag for tag in chat_type.tags] if chat_type.tags else []
    
    data = {
        "id": chat_type.id,
        "name": chat_type.name,
        "description": chat_type.description,
        "tags": tags,
        "is_public": chat_type.is_public,
        "owner_id": chat_type.owner_id,
        "collection_name": chat_type.collection_name,
        "created_at": chat_type.created_at,
        "owner_name": owner_name,
        "is_favorited": is_favorited
    }
    return data


@router.post("/", response_model=ChatTypeResponse, status_code=status.HTTP_201_CREATED)
def create_chat_type(
    chat_type_data: ChatTypeCreate,
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    favorite_repo: ChatTypeFavoriteRepository = Depends(get_chat_type_favorite_repo)
):
    """
    Create a new ChatType.
    Creates both the database record and the Qdrant collection.
    """
    try:
        
        # Generate collection name
        collection_name = f"chat_type_{chat_type_data.name.lower().replace(' ', '_')}"
        
        # Check if name already exists
        existing = chat_type_repo.get_by_name(chat_type_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ChatType with name '{chat_type_data.name}' already exists"
            )
        
        # Create database record
        chat_type = ChatType(
            name=chat_type_data.name,
            description=chat_type_data.description,
            is_public=chat_type_data.is_public,
            owner_id=current_user.id,
            collection_name=collection_name
        )
        
        chat_type = chat_type_repo.create(chat_type)
        
        # Add tags if provided
        if chat_type_data.tags:
            chat_type_repo.add_tags(chat_type.id, chat_type_data.tags)
        
        # Create Qdrant collection
        try:
            qdrant = QdrantManager()
            qdrant.create_collection(chat_type.id, vector_size=1024)
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection for ChatType {chat_type.id}: {e}")
            # Rollback: delete the created chat_type
            chat_type_repo.delete(chat_type)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create vector collection: {str(e)}"
            )
        
        logger.info(f"Created ChatType: {chat_type.name} (id={chat_type.id})")
        
        # Load owner relationship and tags
        chat_type = chat_type_repo.get_by_id(chat_type.id, load_owner=True)
        return ChatTypeResponse(**enrich_chat_type_with_owner(chat_type, favorite_repo, current_user.id))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create ChatType: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat type: {str(e)}"
        )


@router.get("/search", response_model=ChatTypeListResponse)
def search_chat_types(
    query: Optional[str] = Query(None, description="Search in name and description"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    owner_id: Optional[UUID] = Query(None, description="Filter by owner"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    favorite_repo: ChatTypeFavoriteRepository = Depends(get_chat_type_favorite_repo)
):
    """
    Search and filter chat types with advanced options.
    Users only see public chat types or their own.
    Supports text search in name and description.
    """
    try:
        
        chat_types, total = chat_type_repo.search(
            query=query,
            is_public=is_public,
            owner_id=owner_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        
        enriched_chat_types = [ChatTypeResponse(**enrich_chat_type_with_owner(ct, favorite_repo, current_user.id)) for ct in chat_types]
        
        return ChatTypeListResponse(chat_types=enriched_chat_types, total=total)
        
    except Exception as e:
        logger.error(f"Failed to search chat types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search chat types: {str(e)}"
        )


@router.get("/", response_model=ChatTypeListResponse)
def list_chat_types(
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    owner_id: Optional[UUID] = Query(None, description="Filter by owner"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    favorite_repo: ChatTypeFavoriteRepository = Depends(get_chat_type_favorite_repo)
):
    """
    List chat types available to the user (Steam Workshop style).
    Shows only:
    - Private chat types owned by the user
    - Public chat types favorited by the user
    
    For browsing all public chat types, use /search endpoint.
    """
    try:
        
        favorited_ids = favorite_repo.get_user_favorite_ids(current_user.id)
        
        chat_types, total = chat_type_repo.list_user_available(
            user_id=current_user.id,
            favorited_ids=favorited_ids,
            is_public=is_public,
            owner_id=owner_id,
            skip=skip,
            limit=limit
        )
        
        enriched_chat_types = [ChatTypeResponse(**enrich_chat_type_with_owner(ct, favorite_repo, current_user.id)) for ct in chat_types]
        
        return ChatTypeListResponse(chat_types=enriched_chat_types, total=total)
        
    except Exception as e:
        logger.error(f"Failed to list chat types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chat types: {str(e)}"
        )


@router.get("/{chat_type_id}", response_model=ChatTypeResponse)
def get_chat_type(
    chat_type_id: UUID,
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    favorite_repo: ChatTypeFavoriteRepository = Depends(get_chat_type_favorite_repo)
):
    """
    Get a specific chat type by ID.
    Checks if user has access (public or owner).
    """
    
    chat_type = chat_type_repo.get_by_id(chat_type_id, load_owner=True)
    
    if not chat_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ChatType with id {chat_type_id} not found"
        )
    
    # Check access
    if not chat_type.is_public and chat_type.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this chat type"
        )
    
    return ChatTypeResponse(**enrich_chat_type_with_owner(chat_type, favorite_repo, current_user.id))


@router.patch("/{chat_type_id}", response_model=ChatTypeResponse)
def update_chat_type(
    chat_type_id: UUID,
    chat_type_data: ChatTypeUpdate,
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    favorite_repo: ChatTypeFavoriteRepository = Depends(get_chat_type_favorite_repo)
):
    """
    Update a chat type (name, description, is_public, tags).
    Only the owner can update it. All fields are optional.
    """
    try:
        
        chat_type = chat_type_repo.get_by_id(chat_type_id, load_owner=True)
        
        if not chat_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ChatType with id {chat_type_id} not found"
            )
        
        # Check ownership
        if chat_type.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this chat type"
            )
        
        # Update only provided fields
        if chat_type_data.name is not None:
            chat_type.name = chat_type_data.name
        if chat_type_data.description is not None:
            chat_type.description = chat_type_data.description
        if chat_type_data.is_public is not None:
            chat_type.is_public = chat_type_data.is_public
        
        # Update in database
        chat_type = chat_type_repo.create(chat_type)
        
        # Update tags if provided
        if chat_type_data.tags is not None:
            chat_type_repo.add_tags(chat_type.id, chat_type_data.tags)
        
        logger.info(f"Updated ChatType: {chat_type.name} (id={chat_type.id})")
        
        # Reload to get updated tags
        chat_type = chat_type_repo.get_by_id(chat_type.id, load_owner=True)
        return ChatTypeResponse(**enrich_chat_type_with_owner(chat_type, favorite_repo, current_user.id))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update ChatType {chat_type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat type: {str(e)}"
        )


@router.delete("/{chat_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_type(
    chat_type_id: UUID,
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo)
):
    """
    Delete a chat type and its Qdrant collection.
    Only the owner can delete it.
    """
    try:
        
        chat_type = chat_type_repo.get_by_id(chat_type_id)
        
        if not chat_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ChatType with id {chat_type_id} not found"
            )
        
        # Check ownership
        if chat_type.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this chat type"
            )
        
        # Delete Qdrant collection
        qdrant = QdrantManager()
        qdrant.delete_collection(chat_type_id)
        
        # Delete database record (cascades to chats, messages, chunks)
        chat_type_repo.delete(chat_type)
        
        logger.info(f"Deleted ChatType: {chat_type.name} (id={chat_type_id})")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete ChatType {chat_type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat type: {str(e)}"
        )


@router.get("/{chat_type_id}/info")
def get_chat_type_info(
    chat_type_id: UUID,
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    favorite_repo: ChatTypeFavoriteRepository = Depends(get_chat_type_favorite_repo)
):
    """
    Get detailed info about a chat type including Qdrant collection stats.
    Only the owner can see detailed info.
    """
    
    chat_type = chat_type_repo.get_by_id(chat_type_id, load_owner=True)
    
    if not chat_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ChatType with id {chat_type_id} not found"
        )
    
    # Check ownership
    if chat_type.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view detailed info for this chat type"
        )
    
    try:
        qdrant = QdrantManager()
        collection_info = qdrant.get_collection_info(chat_type_id)
        
        return {
            "chat_type": ChatTypeResponse(**enrich_chat_type_with_owner(chat_type, favorite_repo, current_user.id)),
            "collection_info": collection_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get chat type info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat type info: {str(e)}"
        )


@router.post("/{chat_type_id}/favorite", response_model=ChatTypeFavoriteResponse, status_code=status.HTTP_201_CREATED)
def favorite_chat_type(
    chat_type_id: UUID,
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    favorite_repo: ChatTypeFavoriteRepository = Depends(get_chat_type_favorite_repo)
):
    """
    Add a chat type to user's favorites.
    """
    try:
        
        chat_type = chat_type_repo.get_by_id(chat_type_id)
        
        if not chat_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ChatType with id {chat_type_id} not found"
            )
        
        if not chat_type.is_public and chat_type.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to favorite this chat type"
            )
        
        if favorite_repo.is_favorited(current_user.id, chat_type_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat type is already in favorites"
            )
        
        favorite = favorite_repo.create(current_user.id, chat_type_id)
        
        logger.info(f"User {current_user.id} favorited ChatType {chat_type_id}")
        
        return ChatTypeFavoriteResponse.model_validate(favorite)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to favorite chat type: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to favorite chat type: {str(e)}"
        )


@router.delete("/{chat_type_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def unfavorite_chat_type(
    chat_type_id: UUID,
    current_user: User = Depends(get_current_active_user),
    favorite_repo: ChatTypeFavoriteRepository = Depends(get_chat_type_favorite_repo)
):
    """
    Remove a chat type from user's favorites.
    """
    try:
        
        if not favorite_repo.delete_by_user_and_chat_type(current_user.id, chat_type_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat type is not in favorites"
            )
        
        logger.info(f"User {current_user.id} unfavorited ChatType {chat_type_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unfavorite chat type: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unfavorite chat type: {str(e)}"
        )
