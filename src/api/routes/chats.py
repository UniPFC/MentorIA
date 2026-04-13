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
from src.services.background import schedule_title_generation
from src.services.instant_responses import InstantResponseService
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
from src.api.dependencies import (
    get_current_active_user,
    get_chat_repo,
    get_chat_type_repo
)
from src.repositories.chat import ChatRepository
from src.repositories.chat_type import ChatTypeRepository
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


def verify_chat_ownership(chat_id: UUID, user_id: UUID, chat_repo: ChatRepository) -> Chat:
    """
    Verify that a chat belongs to the specified user.
    
    Args:
        chat_id: ID of the chat
        user_id: ID of the user
        chat_repo: Chat repository instance
        
    Returns:
        Chat object if found and owned by user
        
    Raises:
        HTTPException: If chat not found or doesn't belong to user
    """
    chat = chat_repo.get_by_id(chat_id)
    
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
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    chat_repo: ChatRepository = Depends(get_chat_repo)
):
    """
    Create a new chat session.
    If no title is provided, generates a numbered placeholder (e.g., "Chat #1").
    Title can be auto-generated after first message/response if placeholder was used.
    """
    try:
        
        # Verify chat type exists
        chat_type = chat_type_repo.get_by_id(chat_data.chat_type_id)
        if not chat_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ChatType with id {chat_data.chat_type_id} not found"
            )
        
        # Check access: user must own it or it must be public
        if not chat_type.is_public and chat_type.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create chats with this chat type"
            )
        
        # Determine title and whether it's auto-generated
        title_auto_generated = False
        if chat_data.title:
            title = chat_data.title
        else:
            # Generate numbered placeholder
            user_chats_count = chat_repo.count_by_user(current_user.id)
            title = f"Chat #{user_chats_count + 1}"
            title_auto_generated = True
        
        # Create chat with default model
        chat = Chat(
            user_id=current_user.id,
            chat_type_id=chat_data.chat_type_id,
            title=title,
            title_auto_generated=title_auto_generated,
            llm_model=settings.LLM_MODEL,
            llm_provider=settings.LLM_PROVIDER
        )
        
        chat = chat_repo.create(chat)
        
        logger.info(f"Created Chat: {chat.title} (id={chat.id}, auto_generated={title_auto_generated}, model={chat.llm_model}, provider={chat.llm_provider})")
        return chat
        
    except HTTPException:
        raise
    except Exception as e:
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
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo)
):
    """
    List chats with optional filtering.
    """
    try:
        chats = chat_repo.get_by_user(
            user_id=current_user.id,
            chat_type_id=chat_type_id,
            skip=skip,
            limit=limit
        )
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
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo)
):
    """
    Get a chat with all its messages.
    Only the chat owner can access it.
    """
    chat = verify_chat_ownership(chat_id, current_user.id, chat_repo)
    return chat


@router.patch("/{chat_id}/model", response_model=ChatResponse)
def update_chat_model(
    chat_id: UUID,
    model_update: ChatModelUpdate,
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo),
    db: Session = Depends(get_db)
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
        chat = verify_chat_ownership(chat_id, current_user.id, chat_repo)
        
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
        chat.llm_model = new_model
        chat.llm_provider = new_provider
        chat = chat_repo.update(chat)
        
        logger.info(f"Updated Chat model: {chat_id} -> model={chat.llm_model}, provider={chat.llm_provider}")
        return chat
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update chat model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat model: {str(e)}"
        )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo)
):
    """
    Delete a chat and all its messages.
    """
    try:
        chat = verify_chat_ownership(chat_id, current_user.id, chat_repo)
        chat_repo.delete(chat)
        
        logger.info(f"Deleted Chat: {chat.title} (id={chat_id})")
        
    except HTTPException:
        raise
    except Exception as e:
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
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo)
):
    """
    Send a message and get RAG-powered response.
    Uses the RAG pipeline to retrieve relevant chunks and generate contextual answers.
    Only the chat owner can send messages.
    """
    try:
        # Verify ownership and get chat
        chat = verify_chat_ownership(chat_id, current_user.id, chat_repo)
        
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
        
        schedule_title_generation(chat_id)
        
        logger.info(f"Processed RAG message in chat {chat_id} with {len(retrieved_chunks)} chunks")
        
        # Return full chat with all messages - reload to get updated messages
        chat = chat_repo.get_by_id(chat_id)
        
        return SendMessageResponse(
            chat=ChatWithMessagesResponse.model_validate(chat),
            sources=chunks_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
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
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo)
):
    """
    Send a message and get a streaming RAG-powered response.
    Returns a stream of JSON objects (NDJSON) with 'type' (token/sources/error) and 'content'.
    
    The user message is saved immediately before streaming starts.
    The assistant response is generated and saved completely, even if the client disconnects.
    """
    
    # Verify ownership
    chat = verify_chat_ownership(chat_id, current_user.id, chat_repo)
    
    # Initialize Service
    chat_service = ChatService(db)
    
    # Save User Message immediately (before streaming)
    chat_service.save_message(
        chat_id=chat_id,
        role=MessageRole.USER,
        content=message_data.content
    )
    
    # Get chat history (after saving user message)
    chat_history = chat_service.get_chat_history(chat_id)
    
    # Initialize pipeline
    rag_pipeline = RAGPipeline()
    
    def generate_response():
        # Create a new session for the stream duration
        session = SessionLocal()
        stream_service = ChatService(session)
        
        full_response = []
        retrieved_chunks = []
        client_connected = True
        
        try:
            # Check for instant response first
            instant_response = InstantResponseService.get_instant_response(message_data.content)
            
            if instant_response:
                # Use instant response instead of RAG
                logger.info(f"Using instant response for: '{message_data.content}'")
                
                # Yield the response as tokens (simulate streaming)
                for char in instant_response:
                    full_response.append(char)
                    yield json.dumps({"type": "token", "content": char}) + "\n"
                
                # No sources for instant responses
                yield json.dumps({"type": "sources", "content": []}) + "\n"
            else:
                # Stream generator with chat-specific model if configured
                for chunk in rag_pipeline.run_stream(
                    chat_type_id=chat.chat_type_id,
                    query=message_data.content,
                    chat_history=chat_history,
                    llm_model=chat.llm_model,
                    llm_provider=chat.llm_provider
                ):
                    # Collect data for DB save (regardless of client connection)
                    if chunk["type"] == "token":
                        full_response.append(chunk["content"])
                    elif chunk["type"] == "sources":
                        retrieved_chunks = chunk["content"]
                    
                    # Try to send chunk to client
                    try:
                        yield json.dumps(chunk) + "\n"
                    except GeneratorExit:
                        # Client disconnected, but continue generating
                        client_connected = False
                        logger.info(f"Client disconnected from stream for chat {chat_id}, continuing generation...")
            
            # Save Assistant Message after streaming completes (even if client disconnected)
            assistant_content = "".join(full_response)
            if not assistant_content:
                assistant_content = "Erro ao gerar resposta (sem conteúdo)."
                
            saved_message = stream_service.save_message(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=assistant_content
            )
            
            schedule_title_generation(chat_id)
            
            logger.info(f"Stream completed. Saved assistant message to chat {chat_id}. Client connected: {client_connected}")
            
            # Send final message object only if client is still connected
            if client_connected:
                message_response = MessageResponse.model_validate(saved_message)
                yield json.dumps({
                    "type": "message", 
                    "content": json.loads(message_response.model_dump_json())
                }) + "\n"
            
        except GeneratorExit:
            # Client disconnected
            client_connected = False
            logger.info(f"Client disconnected from chat {chat_id}, saving response...")
            # Continue to save the response
            if full_response:
                try:
                    assistant_content = "".join(full_response)
                    stream_service.save_message(
                        chat_id=chat_id,
                        role=MessageRole.ASSISTANT,
                        content=assistant_content
                    )
                    logger.info(f"Saved complete response to chat {chat_id} after client disconnect")
                    
                except Exception as save_err:
                    logger.error(f"Failed to save response after disconnect: {save_err}")

        except Exception as e:
            logger.error(f"Stream error in chat {chat_id}: {e}")
            session.rollback()
            # Save response if available
            if full_response:
                try:
                    assistant_content = "".join(full_response)
                    stream_service.save_message(
                        chat_id=chat_id,
                        role=MessageRole.ASSISTANT,
                        content=assistant_content
                    )
                    logger.info(f"Saved response to chat {chat_id} after error")
                except Exception as save_err:
                    logger.error(f"Failed to save response after error: {save_err}")
            
            if client_connected:
                try:
                    yield json.dumps({"type": "error", "content": f"Erro no processamento: {str(e)}"}) + "\n"
                except GeneratorExit:
                    pass
        finally:
            session.close()

    return StreamingResponse(generate_response(), media_type="application/x-ndjson")
