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
from src.api.schemas.chat_type import (
    ChatTypeCreate,
    ChatTypeResponse,
    ChatTypeListResponse,
    ChatTypeSearchParams
)
from src.api.dependencies import get_current_active_user
from shared.database.models.user import User
from shared.qdrant.client import QdrantManager
from config.logger import logger

router = APIRouter(prefix="/chat-types", tags=["chat-types"])


def enrich_chat_type_with_owner(chat_type: ChatType) -> dict:
    """
    Helper function to add owner_name to ChatType response.
    Returns dict compatible with ChatTypeResponse schema.
    Chat types owned by user 'MentorIA' are system chat types.
    """
    # Get owner username from loaded relationship
    owner_name = chat_type.owner.username if chat_type.owner else None
    
    data = {
        "id": chat_type.id,
        "name": chat_type.name,
        "description": chat_type.description,
        "is_public": chat_type.is_public,
        "owner_id": chat_type.owner_id,
        "collection_name": chat_type.collection_name,
        "created_at": chat_type.created_at,
        "owner_name": owner_name
    }
    return data


@router.post("/", response_model=ChatTypeResponse, status_code=status.HTTP_201_CREATED)
def create_chat_type(
    chat_type_data: ChatTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new ChatType.
    Creates both the database record and the Qdrant collection.
    """
    try:
        # Generate collection name
        collection_name = f"chat_type_{chat_type_data.name.lower().replace(' ', '_')}"
        
        # Check if name already exists
        existing = db.query(ChatType).filter(ChatType.name == chat_type_data.name).first()
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
            owner_id=current_user.id,  # Usar ID do usuário autenticado
            collection_name=collection_name
        )
        
        db.add(chat_type)
        db.commit()
        db.refresh(chat_type)
        
        # Create Qdrant collection
        try:
            qdrant = QdrantManager()
            qdrant.create_collection(chat_type.id, vector_size=1024)
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection for ChatType {chat_type.id}: {e}")
            # Rollback: delete the created chat_type
            db.delete(chat_type)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create vector collection: {str(e)}"
            )
        
        logger.info(f"Created ChatType: {chat_type.name} (id={chat_type.id})")
        
        # Load owner relationship with explicit query
        chat_type = db.query(ChatType).options(joinedload(ChatType.owner)).filter(ChatType.id == chat_type.id).first()
        return ChatTypeResponse(**enrich_chat_type_with_owner(chat_type))
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search and filter chat types with advanced options.
    Users only see public chat types or their own.
    Supports text search in name and description.
    """
    try:
        # Start query with eager loading of owner
        db_query = db.query(ChatType).options(joinedload(ChatType.owner))
        
        # Security filter: Public OR Owned by user
        db_query = db_query.filter(
            or_(
                ChatType.is_public == True,
                ChatType.owner_id == current_user.id
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
        
        # Get total count
        total = db_query.count()
        
        # Apply pagination and execute
        chat_types = db_query.offset(skip).limit(limit).all()
        
        # Enrich with owner information
        enriched_chat_types = [ChatTypeResponse(**enrich_chat_type_with_owner(ct)) for ct in chat_types]
        
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all chat types with optional filtering.
    Users only see public chat types or their own.
    For advanced search with text query, use /search endpoint.
    """
    try:
        # Use eager loading for owner relationship
        db_query = db.query(ChatType).options(joinedload(ChatType.owner))
        
        # Security filter: Public OR Owned by user
        db_query = db_query.filter(
            or_(
                ChatType.is_public == True,
                ChatType.owner_id == current_user.id
            )
        )
        
        if is_public is not None:
            db_query = db_query.filter(ChatType.is_public == is_public)
        
        if owner_id is not None:
            db_query = db_query.filter(ChatType.owner_id == owner_id)
        
        total = db_query.count()
        chat_types = db_query.offset(skip).limit(limit).all()
        
        # Enrich with owner information
        enriched_chat_types = [ChatTypeResponse(**enrich_chat_type_with_owner(ct)) for ct in chat_types]
        
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific chat type by ID.
    Checks if user has access (public or owner).
    """
    chat_type = db.query(ChatType).options(joinedload(ChatType.owner)).filter(ChatType.id == chat_type_id).first()
    
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
    
    return ChatTypeResponse(**enrich_chat_type_with_owner(chat_type))


@router.delete("/{chat_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_type(
    chat_type_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a chat type and its Qdrant collection.
    Only the owner can delete it.
    """
    try:
        chat_type = db.query(ChatType).filter(ChatType.id == chat_type_id).first()
        
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
        db.delete(chat_type)
        db.commit()
        
        logger.info(f"Deleted ChatType: {chat_type.name} (id={chat_type_id})")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete ChatType {chat_type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat type: {str(e)}"
        )


@router.get("/{chat_type_id}/info")
def get_chat_type_info(
    chat_type_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed info about a chat type including Qdrant collection stats.
    Only the owner can see detailed info.
    """
    chat_type = db.query(ChatType).options(joinedload(ChatType.owner)).filter(ChatType.id == chat_type_id).first()
    
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
            "chat_type": ChatTypeResponse(**enrich_chat_type_with_owner(chat_type)),
            "collection_info": collection_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get chat type info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat type info: {str(e)}"
        )
