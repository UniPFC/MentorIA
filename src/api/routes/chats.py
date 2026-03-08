"""
Chat endpoints for managing chat sessions and messages.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from shared.database.session import get_db
from shared.database.models.chat import Chat
from shared.database.models.chat_type import ChatType
from shared.database.models.message import Message, MessageRole
from shared.database.models.user import User
from src.api.schemas.chat import (
    ChatCreate,
    ChatResponse,
    ChatWithMessagesResponse,
    SendMessageRequest,
    SendMessageResponse,
    MessageResponse
)
from src.api.dependencies import get_current_active_user
from config.logger import logger

router = APIRouter(prefix="/chats", tags=["chats"])


def verify_chat_ownership(chat_id: int, user_id: int, db: Session) -> Chat:
    """
    Verify that a chat belongs to the specified user.
    
    Args:
        chat_id: ID of the chat
        user_id: ID of the user
        db: Database session
        
    Returns:
        Chat object if found and owned by user
        
    Raises:
        HTTPException: If chat not found or doesn't belong to user
    """
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with id {chat_id} not found"
        )
    
    if chat.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this chat"
        )
    
    return chat


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    chat_data: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new chat session.
    """
    try:
        # Verify chat type exists
        chat_type = db.query(ChatType).filter(ChatType.id == chat_data.chat_type_id).first()
        if not chat_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ChatType with id {chat_data.chat_type_id} not found"
            )
        
        # Create chat
        chat = Chat(
            user_id=current_user.id,  # Usar ID do usuário autenticado
            chat_type_id=chat_data.chat_type_id,
            title=chat_data.title
        )
        
        db.add(chat)
        db.commit()
        db.refresh(chat)
        
        logger.info(f"Created Chat: {chat.title} (id={chat.id})")
        return chat
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat: {str(e)}"
        )


@router.get("/", response_model=List[ChatResponse])
def list_chats(
    user_id: int = None,
    chat_type_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List chats with optional filtering.
    """
    try:
        query = db.query(Chat)
        
        if user_id is not None:
            query = query.filter(Chat.user_id == user_id)
        
        if chat_type_id is not None:
            query = query.filter(Chat.chat_type_id == chat_type_id)
        
        chats = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit).all()
        return chats
        
    except Exception as e:
        logger.error(f"Failed to list chats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chats: {str(e)}"
        )


@router.get("/{chat_id}", response_model=ChatWithMessagesResponse)
def get_chat(
    chat_id: int,
    user_id: int,  # TODO: Replace with authenticated user from JWT token
    db: Session = Depends(get_db)
):
    """
    Get a chat with all its messages.
    Only the chat owner can access it.
    """
    chat = verify_chat_ownership(chat_id, user_id, db)
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    user_id: int,  # TODO: Replace with authenticated user from JWT token
    db: Session = Depends(get_db)
):
    """
    Delete a chat and all its messages.
    """
    try:
        chat = verify_chat_ownership(chat_id, user_id, db)
        db.delete(chat)
        db.commit()
        
        logger.info(f"Deleted Chat: {chat.title} (id={chat_id})")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete chat {chat_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat: {str(e)}"
        )


@router.post("/{chat_id}/messages", response_model=SendMessageResponse)
def send_message(
    chat_id: int,
    message_data: SendMessageRequest,
    user_id: int,  # TODO: Replace with authenticated user from JWT token
    db: Session = Depends(get_db)
):
    """
    Send a message and get RAG-powered response.
    Uses the RAG pipeline to retrieve relevant chunks and generate contextual answers.
    Only the chat owner can send messages.
    """
    try:
        # Verify ownership and get chat
        chat = verify_chat_ownership(chat_id, user_id, db)
        
        # Create user message
        user_message = Message(
            chat_id=chat_id,
            role=MessageRole.USER,
            content=message_data.content
        )
        db.add(user_message)
        db.flush()
        
        # Get chat history (last 10 messages for context)
        previous_messages = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.id < user_message.id
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        # Build chat history in reverse order (oldest first)
        chat_history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in reversed(previous_messages)
        ]
        
        # Run RAG pipeline
        from src.rag.pipeline import RAGPipeline
        rag_pipeline = RAGPipeline()
        
        result = rag_pipeline.run(
            chat_type_id=chat.chat_type_id,
            query=message_data.content,
            chat_history=chat_history if chat_history else None
        )
        
        assistant_content = result["answer"]
        retrieved_chunks = result["chunks"]
        
        # Create assistant message
        assistant_message = Message(
            chat_id=chat_id,
            role=MessageRole.ASSISTANT,
            content=assistant_content
        )
        db.add(assistant_message)
        
        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)
        db.refresh(chat)
        
        logger.info(f"Processed RAG message in chat {chat_id} with {len(retrieved_chunks)} chunks")
        
        # Format chunks for response
        chunks_response = [
            {
                "question": chunk["question"],
                "answer": chunk["answer"],
                "score": chunk.get("rerank_score", chunk.get("score", 0))
            }
            for chunk in retrieved_chunks
        ]
        
        # Return full chat with all messages
        return SendMessageResponse(
            chat=ChatWithMessagesResponse.model_validate(chat),
            retrieved_chunks=chunks_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )
