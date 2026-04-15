"""
Background task handlers for long-running operations.
"""

import json
import threading
from datetime import datetime, timezone
from uuid import UUID
from pathlib import Path
from sqlalchemy.orm import Session
from config.logger import logger
from config.settings import settings
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus
from shared.database.models.knowledge_chunk import KnowledgeChunk
from shared.database.models.chat import Chat
from shared.database.models.message import Message, MessageRole
from shared.database.session import SessionLocal
from shared.qdrant.client import QdrantManager
from src.services.ingestion import ChunkIngestionService
from src.ai.provider.llm import Provider
from src.api.schemas.title_generation import ChatTitleResponse


def process_ingestion_job(
    job_id: UUID,
    chat_type_id: UUID,
    file_content: bytes,
    filename: str,
    question_col: str,
    answer_col: str,
    ingestion_service: ChunkIngestionService,
    db: Session
):
    """
    Background task to process chunk ingestion.
    
    Args:
        job_id: ID of the IngestionJob
        chat_type_id: ID of the ChatType
        file_content: File bytes
        filename: Original filename
        question_col: Column name for questions
        answer_col: Column name for answers
        ingestion_service: ChunkIngestionService instance
        db: Database session
    """
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        logger.error(f"IngestionJob {job_id} not found")
        return
    
    try:
        # Update status to processing
        job.status = IngestionStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"Starting ingestion job {job_id} for chat_type_id={chat_type_id}")
        
        # Parse spreadsheet
        chunks = ingestion_service.parse_spreadsheet(
            file_content, filename, question_col, answer_col
        )
        
        job.total_chunks = len(chunks)
        db.commit()
        
        # Ingest chunks with progress callback
        def on_progress(processed: int):
            try:
                job.processed_chunks = processed
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to update progress: {e}")
                db.rollback()
        
        point_ids, total_ingested = ingestion_service.ingest_chunks(
            chat_type_id=chat_type_id,
            chunks=chunks,
            db_session=db,
            on_progress=on_progress
        )
        
        # Update job status
        job.status = IngestionStatus.COMPLETED
        job.processed_chunks = total_ingested
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"Ingestion job {job_id} completed: {total_ingested} chunks")
        
    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {e}")
        job.status = IngestionStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        # Cleanup: Delete ChatType and Qdrant collection if ingestion failed
        try:
            from src.repositories.chat_type import ChatTypeRepository
            chat_type_repo = ChatTypeRepository(db)
            chat_type = chat_type_repo.get_by_id(chat_type_id)
            
            if chat_type:
                # Delete Qdrant collection
                try:
                    qdrant = QdrantManager()
                    qdrant.delete_collection(chat_type_id)
                except Exception as qdrant_err:
                    logger.warning(f"Failed to delete Qdrant collection for ChatType {chat_type_id}: {qdrant_err}")
                
                # Delete ChatType from database
                chat_type_repo.delete(chat_type)
                logger.info(f"Cleaned up ChatType {chat_type_id} due to ingestion failure")
        except Exception as cleanup_err:
            logger.error(f"Failed to cleanup ChatType {chat_type_id} after ingestion failure: {cleanup_err}")


def _load_title_generation_prompt(system: bool = True) -> str:
    """
    Load the title generation prompt from markdown file.
    
    Args:
        system: If True, load system prompt, otherwise load user prompt
    
    Returns:
        Prompt template string
    """
    filename = "title_generation_system_prompt.md" if system else "title_generation_user_prompt.md"
    prompt_path = Path(settings.PROMPTS_DIR) / "chat" / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _generate_chat_title_internal(chat_id: UUID, db: Session) -> bool:
    """
    Generate a title for the chat using AI based on first user message and assistant response.
    Internal function called by background task.
    
    Args:
        chat_id: ID of the chat
        db: Database session
        
    Returns:
        True if title was updated, False otherwise
    """
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        
        if not chat or not chat.title_auto_generated:
            return False
        
        # Get first user message and assistant response
        first_user_msg = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.role == MessageRole.USER
        ).order_by(Message.created_at.asc()).first()
        
        if not first_user_msg:
            return False
        
        first_assistant_msg = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.role == MessageRole.ASSISTANT
        ).order_by(Message.created_at.asc()).first()
        
        # Build context for title generation
        user_question = first_user_msg.content[:500]
        assistant_response = first_assistant_msg.content[:500] if first_assistant_msg else ""
        
        # Load prompt templates
        system_prompt_template = _load_title_generation_prompt(system=True)
        user_prompt_template = _load_title_generation_prompt(system=False)
        
        # Format user prompt with context
        user_prompt = user_prompt_template.format(
            user_question=user_question,
            assistant_response=assistant_response
        )

        llm_provider = Provider(
            model_name=settings.LLM_MODEL,
            provider_alias=settings.LLM_PROVIDER
        )
        
        messages = [
            {"role": "system", "content": system_prompt_template},
            {"role": "user", "content": user_prompt}
        ]
        
        response = llm_provider.generate_structured(
            messages=messages,
            response_format=ChatTitleResponse,
            max_new_tokens=50,
            temperature=0.3
        )
        
        # Extract title from structured response
        if isinstance(response, ChatTitleResponse):
            title = response.title
        else:
            # Fallback if response is raw content
            title = str(response).strip().strip('"').strip("'")
        
        if not title:
            return False
        
        # Update chat with generated title
        chat.title = title
        chat.title_auto_generated = False
        db.commit()
        
        logger.info(f"Generated chat title: {chat_id} -> '{title}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate chat title: {e}")
        db.rollback()
        return False


def generate_chat_title_background(chat_id: UUID) -> None:
    """
    Generate chat title in background thread to avoid blocking the API.
    Creates a new database session for the background task.
    
    Args:
        chat_id: ID of the chat to generate title for
    """
    def _generate():
        session = None
        try:
            session = SessionLocal()
            _generate_chat_title_internal(chat_id, session)
        except Exception as e:
            logger.error(f"Background task failed to generate title for chat {chat_id}: {e}")
        finally:
            if session:
                session.close()
    
    # Start background thread
    thread = threading.Thread(target=_generate, daemon=True)
    thread.start()


def schedule_title_generation(chat_id: UUID) -> None:
    """
    Schedule title generation as a background task.
    Non-blocking call that returns immediately.
    
    Args:
        chat_id: ID of the chat to generate title for
    """
    try:
        generate_chat_title_background(chat_id)
        logger.debug(f"Scheduled background title generation for chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to schedule title generation: {e}")
