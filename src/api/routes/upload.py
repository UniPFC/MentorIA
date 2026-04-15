"""
Upload endpoints for creating chat types from spreadsheets.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from shared.database.session import get_db
from shared.database.models.chat_type import ChatType
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus
from shared.database.models.user import User
from src.api.schemas.upload import UploadResponse
from src.api.schemas.ingestion import UploadResponseAsync, IngestionJobResponse
from src.services.ingestion import ChunkIngestionService
from src.services.background import process_ingestion_job
from src.ai.loader import ModelLoader
from src.ai.provider.embedding import HFEmbeddingProvider
from src.ai.embedding import EmbeddingEngine
from src.api.dependencies import (
    get_current_active_user,
    get_chat_type_repo,
    get_ingestion_job_repo
)
from src.repositories.chat_type import ChatTypeRepository
from src.repositories.ingestion_job import IngestionJobRepository
from shared.qdrant.client import QdrantManager
from config.settings import settings
from config.logger import logger
import json

router = APIRouter(prefix="/upload", tags=["upload"])


def get_ingestion_service() -> ChunkIngestionService:
    """Dependency to get ingestion service with loaded models."""
    loader = ModelLoader()
    emb_model, emb_tokenizer = loader.load_embedding(settings.EMBEDDING_MODEL_ID)
    emb_provider = HFEmbeddingProvider(emb_model, emb_tokenizer)
    emb_engine = EmbeddingEngine(emb_provider)
    qdrant = QdrantManager()
    
    return ChunkIngestionService(emb_engine, qdrant)


@router.post("/chat-type", response_model=UploadResponseAsync, status_code=status.HTTP_202_ACCEPTED)
async def create_chat_type_from_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Excel or CSV file with questions and answers"),
    name: str = Form(..., description="Name of the chat type"),
    description: Optional[str] = Form(None, description="Description"),
    is_public: bool = Form(False, description="Whether chat type is public"),
    question_column: str = Form("question", description="Column name for questions"),
    answer_column: str = Form("answer", description="Column name for answers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    ingestion_service: ChunkIngestionService = Depends(get_ingestion_service),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo),
    job_repo: IngestionJobRepository = Depends(get_ingestion_job_repo)
):
    """
    Create a new ChatType from an uploaded spreadsheet.
    
    The file should contain at least two columns:
    - One for questions (default: 'question')
    - One for answers (default: 'answer')
    
    Supported formats: .xlsx, .xls, .csv
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be Excel (.xlsx, .xls) or CSV (.csv)"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Generate collection name
        collection_name = f"chat_type_{name.lower().replace(' ', '_')}"
        
        # Check if name already exists
        existing = chat_type_repo.get_by_name(name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ChatType with name '{name}' already exists"
            )
        
        # Create ChatType record
        chat_type = ChatType(
            name=name,
            description=description,
            is_public=is_public,
            owner_id=current_user.id,
            collection_name=collection_name
        )
        
        chat_type = chat_type_repo.create(chat_type)
        
        logger.info(f"Created ChatType: {name} (id={chat_type.id})")
        
        # Create Qdrant collection
        try:
            qdrant = QdrantManager()
            qdrant.create_collection(chat_type.id, vector_size=1024)
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection for ChatType {chat_type.id}: {e}")
            chat_type_repo.delete(chat_type)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create vector collection: {str(e)}"
            )
        
        # Create ingestion job
        job = job_repo.create(
            IngestionJob(
                chat_type_id=chat_type.id,
                filename=file.filename,
                status=IngestionStatus.PENDING
            )
        )
        
        logger.info(f"Created ingestion job {job.id} for ChatType {chat_type.id}")
        
        # Schedule background task
        background_tasks.add_task(
            process_ingestion_job,
            job_id=job.id,
            chat_type_id=chat_type.id,
            file_content=file_content,
            filename=file.filename,
            question_col=question_column,
            answer_col=answer_column,
            ingestion_service=ingestion_service,
            db=db
        )
        
        return UploadResponseAsync(
            job_id=job.id,
            chat_type_id=chat_type.id,
            message=f"ChatType '{name}' created. Processing {file.filename} in background.",
            status_url=f"/api/v1/upload/jobs/{job.id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat type from file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat type from file: {str(e)}"
        )


@router.post("/{chat_type_id}/chunks", response_model=UploadResponse)
async def add_chunks_to_chat_type(
    chat_type_id: UUID,
    file: UploadFile = File(..., description="Excel or CSV file with questions and answers"),
    question_column: str = Form("question", description="Column name for questions"),
    answer_column: str = Form("answer", description="Column name for answers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    ingestion_service: ChunkIngestionService = Depends(get_ingestion_service),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo)
):
    """
    Add more chunks to an existing ChatType.
    """
    try:
        
        # Verify chat type exists
        chat_type = chat_type_repo.get_by_id(chat_type_id)
        if not chat_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ChatType with id {chat_type_id} not found"
            )
        
        # Verify ownership
        if chat_type.owner_id != current_user.id:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this chat type"
            )
        
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be Excel (.xlsx, .xls) or CSV (.csv)"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Ingest chunks
        point_ids, total_ingested = ingestion_service.ingest_from_file(
            chat_type_id=chat_type_id,
            file_content=file_content,
            filename=file.filename,
            db_session=db,
            question_col=question_column,
            answer_col=answer_column
        )
        
        logger.info(f"Added {total_ingested} chunks to ChatType {chat_type_id}")
        
        return UploadResponse(
            chat_type_id=chat_type_id,
            chunks_ingested=total_ingested,
            message=f"Successfully added {total_ingested} chunks to chat type '{chat_type.name}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add chunks: {str(e)}"
        )
