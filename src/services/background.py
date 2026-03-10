"""
Background task handlers for long-running operations.
"""

import json
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from config.logger import logger
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus
from shared.database.models.knowledge_chunk import KnowledgeChunk
from src.services.ingestion import ChunkIngestionService


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
        
        # Ingest chunks
        point_ids, total_ingested = ingestion_service.ingest_chunks(
            chat_type_id=chat_type_id,
            chunks=chunks
        )
        
        # Create KnowledgeChunk records
        for point_id in point_ids:
            chunk = KnowledgeChunk(
                chat_type_id=chat_type_id,
                qdrant_point_id=point_id,
                source_file=filename,
                chunk_metadata=json.dumps({"uploaded": True})
            )
            db.add(chunk)
        
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
