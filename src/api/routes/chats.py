"""
Chat endpoints for managing chat sessions and messages.
"""

import asyncio
import json
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.logger import logger
from config.settings import settings
from shared.database.models.chat import Chat
from shared.database.models.message import MessageRole
from shared.database.models.user import User
from shared.database.session import SessionLocal, get_db
from src.api.dependencies import (
    get_chat_repo,
    get_chat_type_repo,
    get_current_active_user,
)
from src.api.schemas.chat import (
    AvailableModelsResponse,
    ChatCreate,
    ChatModelUpdate,
    ChatResponse,
    ChatWithMessagesResponse,
    LLMModelInfo,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from src.repositories.chat import ChatRepository
from src.repositories.chat_type import ChatTypeRepository
from src.services.background import schedule_title_generation
from src.services.chat import ChatService
from src.services.instant_responses import InstantResponseService
from src.services.tokenizer import (
    count_tokens,
    mode_from_provider,
)
from src.services.user import UserService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/models/available", response_model=AvailableModelsResponse)
def get_available_models(current_user: User = Depends(get_current_active_user)):
    """
    Get list of available LLM models and providers from settings.
    Returns configured models that can be used in chats.
    """
    try:
        available_models_data = settings.get_available_models()
        available_models = []

        for m in available_models_data:
            input_mult = m.get("input_token_multiplier", 1.0)
            output_mult = m.get("output_token_multiplier", 1.0)
            avg_mult = (input_mult + output_mult) / 2

            # Calculate cost tier (0-9)
            # Range: COST_TIER_MIN_MULTIPLIER = 0, COST_TIER_MAX_MULTIPLIER = 9
            min_mult = settings.COST_TIER_MIN_MULTIPLIER
            max_mult = settings.COST_TIER_MAX_MULTIPLIER
            tier = int(((avg_mult - min_mult) / (max_mult - min_mult)) * 9)
            tier = max(0, min(9, tier))

            available_models.append(
                LLMModelInfo(
                    model=m.get("model"),
                    provider=m.get("provider"),
                    description=m.get("description"),
                    cost_tier=tier,
                )
            )

        current_default = f"{settings.LLM_MODEL} ({settings.LLM_PROVIDER})"

        logger.info(
            f"Listed {len(available_models)} available models for user {current_user.id}"
        )

        return AvailableModelsResponse(
            models=available_models, current_default=current_default
        )

    except Exception as e:
        logger.error(f"Failed to list available models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list available models: {str(e)}",
        )


def verify_chat_ownership(
    chat_id: UUID, user_id: UUID, chat_repo: ChatRepository
) -> Chat:
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
            detail=f"Chat with id {chat_id} not found",
        )

    if chat.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this chat",
        )

    return chat


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_active_user),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    chat_repo: ChatRepository = Depends(get_chat_repo),
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
                detail=f"ChatType with id {chat_data.chat_type_id} not found",
            )

        # Check access: user must own it or it must be public
        if not chat_type.is_public and chat_type.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create chats with this chat type",
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
            llm_provider=settings.LLM_PROVIDER,
        )

        chat = chat_repo.create(chat)

        logger.info(
            f"Created Chat: {chat.title} (id={chat.id}, auto_generated={title_auto_generated}, model={chat.llm_model}, provider={chat.llm_provider})"
        )
        return chat

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat: {str(e)}",
        )


@router.get("/", response_model=list[ChatResponse])
def list_chats(
    chat_type_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo),
):
    """
    List chats with optional filtering.
    """
    try:
        chats = chat_repo.get_by_user(
            user_id=current_user.id, chat_type_id=chat_type_id, skip=skip, limit=limit
        )
        return chats

    except Exception as e:
        logger.error(f"Failed to list chats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chats: {str(e)}",
        )


@router.get("/{chat_id}", response_model=ChatWithMessagesResponse)
def get_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo),
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
    db: Session = Depends(get_db),
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
        new_model = (
            model_update.llm_model
            if model_update.llm_model is not None
            else chat.llm_model
        )
        new_provider = (
            model_update.llm_provider
            if model_update.llm_provider is not None
            else chat.llm_provider
        )

        # Validate that the new model/provider combination is available
        if (new_model, new_provider) not in available_model_pairs:
            available_list = ", ".join(
                [f"{m['model']} ({m['provider']})" for m in available_models]
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{new_model}' with provider '{new_provider}' is not available. Available models: {available_list}",
            )

        # Update the chat
        chat.llm_model = new_model
        chat.llm_provider = new_provider
        chat = chat_repo.update(chat)

        logger.info(
            f"Updated Chat model: {chat_id} -> model={chat.llm_model}, provider={chat.llm_provider}"
        )
        return chat

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update chat model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat model: {str(e)}",
        )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo),
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
            detail=f"Failed to delete chat: {str(e)}",
        )


@router.post("/{chat_id}/messages", response_model=SendMessageResponse)
async def send_message(
    chat_id: UUID,
    message_data: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo),
):
    """
    Send a message and get RAG-powered response.
    Uses the RAG pipeline to retrieve relevant chunks and generate contextual answers.
    Only the chat owner can send messages.

    Async endpoint: offloads blocking RAG pipeline to a thread so the event loop
    stays free for other requests.
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa verificar seu email para enviar mensagens.",
        )

    try:
        # Verify ownership and get chat (offload sync DB call)
        chat = await asyncio.to_thread(
            verify_chat_ownership, chat_id, current_user.id, chat_repo
        )

        if chat.is_read_only:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta base de conhecimento tornou-se privada ou foi excluída. Este chat agora é Somente Leitura.",
            )

        # Initialize Service
        chat_service = ChatService(db)

        # Save User Message (offload sync DB call)
        await asyncio.to_thread(
            chat_service.save_message,
            chat_id=chat_id,
            role=MessageRole.USER,
            content=message_data.content,
        )

        # Get chat history (offload sync DB call)
        chat_history = await asyncio.to_thread(chat_service.get_chat_history, chat_id)

        # Count input tokens before calling the AI
        token_mode = mode_from_provider(chat.llm_provider)
        input_tokens = count_tokens(message_data.content, mode=token_mode)
        logger.info(
            f"[INPUT TOKENS] chat={chat_id} provider={chat.llm_provider or 'default'} model={chat.llm_model or 'default'} tokens={input_tokens}"
        )

        # Check user token budget before sending message
        user_service = UserService(db)

        # Get model cost multipliers
        available_models = settings.get_available_models()
        input_multiplier = 1.0
        output_multiplier = 1.0
        for model in available_models:
            if (
                model["model"] == chat.llm_model
                and model["provider"] == chat.llm_provider
            ):
                input_multiplier = model.get("input_token_multiplier", 1.0)
                output_multiplier = model.get("output_token_multiplier", 1.0)
                break

        # Check if user can afford input tokens + reserve (only check input, not output)
        actual_input_tokens = int(input_tokens * input_multiplier)
        if not user_service.can_afford_tokens(
            current_user,
            input_tokens,
            0,
            settings.TOKEN_BUDGET_MINIMUM_RESERVE,
            input_multiplier,
            1.0,
        ):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient token budget. Remaining: {current_user.token_budget}, Required: {actual_input_tokens + settings.TOKEN_BUDGET_MINIMUM_RESERVE} (input*{input_multiplier} + reserve)",
            )

        try:
            # timeout=None is used because if the worker is busy, the request will wait in the worker's queue.
            async with httpx.AsyncClient(timeout=None) as client:
                response = await client.post(
                    f"{settings.AI_WORKER_URL}/internal/generate",
                    json={
                        "chat_type_id": str(chat.chat_type_id),
                        "query": message_data.content,
                        "chat_history": chat_history if chat_history else None,
                        "llm_model": chat.llm_model,
                        "llm_provider": chat.llm_provider,
                    },
                    headers={"X-Internal-Token": settings.INTERNAL_API_KEY},
                )
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error calling AI worker: {e}")
            raise HTTPException(
                status_code=500,
                detail="Ocorreu um erro no processamento da inteligência artificial. Tente novamente.",
            )

        assistant_content = result["answer"]
        retrieved_chunks = result["chunks"]

        # Token usage logging
        output_tokens = count_tokens(assistant_content, mode=token_mode)
        logger.info(
            f"[OUTPUT TOKENS] chat={chat_id} provider={chat.llm_provider or 'default'} model={chat.llm_model or 'default'} tokens={output_tokens}"
        )
        logger.info(
            f"[TOKEN USAGE] chat={chat_id} provider={chat.llm_provider or 'default'} "
            f"model={chat.llm_model or 'default'} input_tokens={input_tokens} output_tokens={output_tokens} "
            f"total_tokens={input_tokens + output_tokens}"
        )

        # Deduct tokens from user budget
        user_service.deduct_tokens(
            current_user.id,
            input_tokens,
            output_tokens,
            input_multiplier,
            output_multiplier,
        )

        # Format chunks for response (and storage)
        chunks_response = [
            {
                "question": chunk["question"],
                "answer": chunk["answer"],
                "score": chunk.get("rerank_score", chunk.get("score", 0)),
            }
            for chunk in retrieved_chunks
        ]

        # Save Assistant Message with context (offload sync DB call)
        await asyncio.to_thread(
            chat_service.save_message,
            chat_id=chat_id,
            role=MessageRole.ASSISTANT,
            content=assistant_content,
        )

        schedule_title_generation(chat_id)

        logger.info(
            f"Processed RAG message in chat {chat_id} with {len(retrieved_chunks)} chunks"
        )

        # Return full chat with all messages - reload to get updated messages (offload sync DB call)
        chat = await asyncio.to_thread(chat_repo.get_by_id, chat_id)  # type: ignore
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        return SendMessageResponse(
            chat=ChatWithMessagesResponse.model_validate(chat), sources=chunks_response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        )


@router.post("/{chat_id}/messages/stream")
async def send_message_stream(
    chat_id: UUID,
    message_data: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repo),
):
    """
    Send a message and get a streaming RAG-powered response.
    Returns a stream of JSON objects (NDJSON) with 'type' (token/sources/error) and 'content'.

    The user message is saved immediately before streaming starts.
    The assistant response is generated and saved completely, even if the client disconnects.

    Async endpoint: the setup phase (verify, save, history) runs without blocking.
    The streaming generator itself runs in a thread via StreamingResponse.
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa verificar seu email para enviar mensagens.",
        )

    # Verify ownership (offload sync DB call)
    chat = await asyncio.to_thread(
        verify_chat_ownership, chat_id, current_user.id, chat_repo
    )

    if chat.chat_type_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta base de conhecimento foi excluída pelo criador original. Este chat agora é Somente Leitura.",
        )

    # Initialize Service
    chat_service = ChatService(db)

    # Save User Message immediately (offload sync DB call)
    await asyncio.to_thread(
        chat_service.save_message,
        chat_id=chat_id,
        role=MessageRole.USER,
        content=message_data.content,
    )

    # Get chat history (offload sync DB call)
    chat_history = await asyncio.to_thread(chat_service.get_chat_history, chat_id)

    # Count input tokens before calling the AI
    token_mode = mode_from_provider(chat.llm_provider)
    input_tokens = count_tokens(message_data.content, mode=token_mode)
    logger.info(
        f"[INPUT TOKENS] chat={chat_id} provider={chat.llm_provider or 'default'} model={chat.llm_model or 'default'} tokens={input_tokens}"
    )

    # Check user token budget before sending message
    user_service = UserService(db)

    # Get model cost multipliers
    available_models = settings.get_available_models()
    input_multiplier = 1.0
    output_multiplier = 1.0
    for model in available_models:
        if model["model"] == chat.llm_model and model["provider"] == chat.llm_provider:
            input_multiplier = model.get("input_token_multiplier", 1.0)
            output_multiplier = model.get("output_token_multiplier", 1.0)
            break

    # Check if user can afford input tokens + reserve (only check input, not output)
    actual_input_tokens = int(input_tokens * input_multiplier)
    if not user_service.can_afford_tokens(
        current_user,
        input_tokens,
        0,
        settings.TOKEN_BUDGET_MINIMUM_RESERVE,
        input_multiplier,
        1.0,
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient token budget. Remaining: {current_user.token_budget}, Required: {actual_input_tokens + settings.TOKEN_BUDGET_MINIMUM_RESERVE} (input*{input_multiplier} + reserve)",
        )

    def generate_response():
        # Create a new session for the stream duration
        session = SessionLocal()
        stream_service = ChatService(session)

        full_response = []
        retrieved_chunks = []
        client_connected = True

        try:
            # Check for instant response first
            instant_response = InstantResponseService.get_instant_response(
                message_data.content
            )

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
                payload = {
                    "chat_type_id": str(chat.chat_type_id),
                    "query": message_data.content,
                    "chat_history": chat_history if chat_history else None,
                    "llm_model": chat.llm_model,
                    "llm_provider": chat.llm_provider,
                }

                try:
                    # timeout=None is used because if the worker is busy, the request will wait in the worker's queue.
                    with httpx.stream(
                        "POST",
                        f"{settings.AI_WORKER_URL}/internal/generate_stream",
                        json=payload,
                        headers={"X-Internal-Token": settings.INTERNAL_API_KEY},
                        timeout=None,
                    ) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line or not line.startswith("data: "):
                                continue

                            chunk_data = line[6:]
                            try:
                                chunk = json.loads(chunk_data)
                            except json.JSONDecodeError:
                                continue

                            # Collect data for DB save (regardless of client connection)
                            if chunk["type"] == "token":
                                full_response.append(chunk["content"])
                            elif chunk["type"] == "sources":
                                retrieved_chunks = chunk["content"]
                            elif chunk["type"] == "error":
                                logger.error(
                                    f"Worker returned error: {chunk.get('content')}"
                                )

                            # Try to send chunk to client
                            if client_connected:
                                try:
                                    yield json.dumps(chunk) + "\n"
                                except GeneratorExit:
                                    # Client disconnected, but continue generating
                                    client_connected = False
                                    logger.info(
                                        f"Client disconnected from stream for chat {chat_id}, continuing generation..."
                                    )
                except httpx.HTTPError as e:
                    logger.error(f"Error streaming from AI worker: {e}")
                    error_chunk = {
                        "type": "error",
                        "content": "Ocorreu um erro no processamento da inteligência artificial. Tente novamente.",
                    }
                    if client_connected:
                        yield json.dumps(error_chunk) + "\n"

            # Save Assistant Message after streaming completes (even if client disconnected)
            assistant_content = "".join(full_response)
            if not assistant_content:
                assistant_content = "Erro ao gerar resposta (sem conteúdo)."

            saved_message = stream_service.save_message(
                chat_id=chat_id, role=MessageRole.ASSISTANT, content=assistant_content
            )

            schedule_title_generation(chat_id)

            # Token usage logging
            output_tokens = count_tokens(assistant_content, mode=token_mode)
            logger.info(
                f"[OUTPUT TOKENS] chat={chat_id} provider={chat.llm_provider or 'default'} model={chat.llm_model or 'default'} tokens={output_tokens}"
            )
            logger.info(
                f"[TOKEN USAGE] chat={chat_id} provider={chat.llm_provider or 'default'} "
                f"model={chat.llm_model or 'default'} input_tokens={input_tokens} output_tokens={output_tokens} "
                f"total_tokens={input_tokens + output_tokens}"
            )

            # Deduct tokens from user budget
            user_service.deduct_tokens(
                current_user.id,
                input_tokens,
                output_tokens,
                input_multiplier,
                output_multiplier,
            )

            logger.info(
                f"Stream completed. Saved assistant message to chat {chat_id}. Client connected: {client_connected}"
            )

            # Send final message object only if client is still connected
            if client_connected:
                message_response = MessageResponse.model_validate(saved_message)
                yield (
                    json.dumps(
                        {
                            "type": "message",
                            "content": json.loads(message_response.model_dump_json()),
                        }
                    )
                    + "\n"
                )

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
                        content=assistant_content,
                    )
                    logger.info(
                        f"Saved complete response to chat {chat_id} after client disconnect"
                    )

                except Exception as save_err:
                    logger.error(
                        f"Failed to save response after disconnect: {save_err}"
                    )

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
                        content=assistant_content,
                    )
                    logger.info(f"Saved response to chat {chat_id} after error")
                except Exception as save_err:
                    logger.error(f"Failed to save response after error: {save_err}")

            if client_connected:
                try:
                    yield (
                        json.dumps(
                            {
                                "type": "error",
                                "content": f"Erro no processamento: {str(e)}",
                            }
                        )
                        + "\n"
                    )
                except GeneratorExit:
                    pass
        finally:
            session.close()

    return StreamingResponse(generate_response(), media_type="application/x-ndjson")
