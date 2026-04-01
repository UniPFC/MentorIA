"""
Chat endpoints for managing chat sessions and messages.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from shared.database.session import get_db, SessionLocal
from shared.database.models.chat import Chat
from shared.database.models.chat_type import ChatType
from shared.database.models.message import Message, MessageRole
from shared.database.models.user import User
from src.services.chat import ChatService
from src.api.schemas.chat import (
    ChatCreate,
    ChatResponse,
    ChatWithMessagesResponse,
    SendMessageRequest,
    SendMessageResponse,
    MessageResponse,
    ChatModelUpdate,
    AvailableModelsResponse,
    LLMModelInfo
)
from src.api.dependencies import get_current_active_user
from src.rag.pipeline import RAGPipeline
from config.settings import settings
import json
from config.logger import logger

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/models/available", response_model=AvailableModelsResponse)
def get_available_models(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of available LLM models and providers from settings.
    Returns configured models that can be used in chats.
    """
    try:
        available_models_data = settings.get_available_models()
        available_models = [
            LLMModelInfo(
                model=m.get("model"),
                provider=m.get("provider"),
                description=m.get("description")
            )
            for m in available_models_data
        ]
        
        current_default = f"{settings.LLM_MODEL} ({settings.LLM_PROVIDER})"
        
        logger.info(f"Listed {len(available_models)} available models for user {current_user.id}")
        
        return AvailableModelsResponse(
            models=available_models,
            current_default=current_default
        )
        
    except Exception as e:
        logger.error(f"Failed to list available models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list available models: {str(e)}"
        )


def verify_chat_ownership(chat_id: UUID, user_id: UUID, db: Session) -> Chat:
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
    Optionally specify llm_model and llm_provider to override defaults.
    """
    try:
        # Verify chat type exists
        chat_type = db.query(ChatType).filter(ChatType.id == chat_data.chat_type_id).first()
        if not chat_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ChatType with id {chat_data.chat_type_id} not found"
            )
        
        # Create chat with default model
        chat = Chat(
            user_id=current_user.id,
            chat_type_id=chat_data.chat_type_id,
            title=chat_data.title,
            llm_model=settings.LLM_MODEL,
            llm_provider=settings.LLM_PROVIDER
        )
        
        db.add(chat)
        db.commit()
        db.refresh(chat)
        
        logger.info(f"Created Chat: {chat.title} (id={chat.id}, model={chat.llm_model}, provider={chat.llm_provider})")
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
    chat_type_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List chats with optional filtering.
    """
    try:
        query = db.query(Chat)
        
        # Filter by current user (always)
        query = query.filter(Chat.user_id == current_user.id)
        
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
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a chat with all its messages.
    Only the chat owner can access it.
    """
    chat = verify_chat_ownership(chat_id, current_user.id, db)
    return chat


@router.patch("/{chat_id}/model", response_model=ChatResponse)
def update_chat_model(
    chat_id: UUID,
    model_update: ChatModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update the LLM model and/or provider for a chat.
    Can be changed at any time during the chat session.
    Model must be one of the available models from settings.
    
    Args:
        chat_id: ID of the chat
        model_update: ChatModelUpdate schema with llm_model and/or llm_provider
    """
    try:
        chat = verify_chat_ownership(chat_id, current_user.id, db)
        
        # Get available models for validation
        available_models = settings.get_available_models()
        available_model_pairs = {(m["model"], m["provider"]) for m in available_models}
        
        # Determine the new model and provider
        new_model = model_update.llm_model if model_update.llm_model is not None else chat.llm_model
        new_provider = model_update.llm_provider if model_update.llm_provider is not None else chat.llm_provider
        
        # Validate that the new model/provider combination is available
        if (new_model, new_provider) not in available_model_pairs:
            available_list = ", ".join([f"{m['model']} ({m['provider']})" for m in available_models])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{new_model}' with provider '{new_provider}' is not available. Available models: {available_list}"
            )
        
        # Update the chat
        if model_update.llm_model is not None:
            chat.llm_model = model_update.llm_model
        if model_update.llm_provider is not None:
            chat.llm_provider = model_update.llm_provider
        
        db.commit()
        db.refresh(chat)
        
        logger.info(f"Updated Chat model: {chat_id} -> model={chat.llm_model}, provider={chat.llm_provider}")
        return chat
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update chat model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat model: {str(e)}"
        )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a chat and all its messages.
    """
    try:
        chat = verify_chat_ownership(chat_id, current_user.id, db)
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
    chat_id: UUID,
    message_data: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a message and get RAG-powered response.
    Uses the RAG pipeline to retrieve relevant chunks and generate contextual answers.
    Only the chat owner can send messages.
    """
    try:
        # Verify ownership and get chat
        chat = verify_chat_ownership(chat_id, current_user.id, db)
        
        # Initialize Service
        chat_service = ChatService(db)
        
        # Save User Message
        chat_service.save_message(
            chat_id=chat_id,
            role=MessageRole.USER,
            content=message_data.content
        )
        
        # Get chat history
        chat_history = chat_service.get_chat_history(chat_id)
        
        # Run RAG pipeline with chat-specific model if configured
        from src.rag.pipeline import RAGPipeline
        rag_pipeline = RAGPipeline()
        
        result = rag_pipeline.run(
            chat_type_id=chat.chat_type_id,
            query=message_data.content,
            chat_history=chat_history if chat_history else None,
            llm_model=chat.llm_model,
            llm_provider=chat.llm_provider
        )
        
        assistant_content = result["answer"]
        retrieved_chunks = result["chunks"]
        
        # Format chunks for response (and storage)
        chunks_response = [
            {
                "question": chunk["question"],
                "answer": chunk["answer"],
                "score": chunk.get("rerank_score", chunk.get("score", 0))
            }
            for chunk in retrieved_chunks
        ]
        
        # Save Assistant Message with context
        chat_service.save_message(
            chat_id=chat_id,
            role=MessageRole.ASSISTANT,
            content=assistant_content
        )
        
        logger.info(f"Processed RAG message in chat {chat_id} with {len(retrieved_chunks)} chunks")
        
        # Return full chat with all messages
        db.refresh(chat)
        
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


@router.post("/{chat_id}/messages/stream")
def send_message_stream(
    chat_id: UUID,
    message_data: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a message and get a streaming RAG-powered response.
    Returns a stream of JSON objects (NDJSON) with 'type' (token/sources/error) and 'content'.
    """
    
    # Verify ownership
    chat = verify_chat_ownership(chat_id, current_user.id, db)
    
    # Initialize Service
    chat_service = ChatService(db)
    
    # Get chat history
    chat_history = chat_service.get_chat_history(chat_id)
    
    # Initialize pipeline
    
    rag_pipeline = RAGPipeline()
    
    async def generate_response():
        # Create a new session for the stream duration
        session = SessionLocal()
        stream_service = ChatService(session)
        
        full_response = []
        retrieved_chunks = []
        
        try:
            # Save User Message immediately
            stream_service.save_message(
                chat_id=chat_id,
                role=MessageRole.USER,
                content=message_data.content
            )
            
            # Stream generator with chat-specific model if configured
            for chunk in rag_pipeline.run_stream(
                chat_type_id=chat.chat_type_id,
                query=message_data.content,
                chat_history=chat_history,
                llm_model=chat.llm_model,
                llm_provider=chat.llm_provider
            ):
                # Send chunk to client
                yield json.dumps(chunk) + "\n"
                
                # Collect data for DB save
                if chunk["type"] == "token":
                    full_response.append(chunk["content"])
                elif chunk["type"] == "sources":
                    retrieved_chunks = chunk["content"]
            
            # Save Assistant Message
            assistant_content = "".join(full_response)
            if not assistant_content:
                assistant_content = "Erro ao gerar resposta (sem conteúdo)."
                
            saved_message = stream_service.save_message(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=assistant_content
            )
            
            # Send final message object
            message_response = MessageResponse.model_validate(saved_message)
            yield json.dumps({
                "type": "message", 
                "content": json.loads(message_response.model_dump_json())
            }) + "\n"
            
            logger.info(f"Stream completed. Saved messages to chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            session.rollback()
            yield json.dumps({"type": "error", "content": f"Erro interno: {str(e)}"}) + "\n"
        finally:
            session.close()

    return StreamingResponse(generate_response(), media_type="application/x-ndjson")
