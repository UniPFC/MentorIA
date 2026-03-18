"""
Job status endpoints for tracking background tasks.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from shared.database.session import get_db
from shared.database.models.ingestion_job import IngestionJob
from shared.database.models.chat_type import ChatType
from shared.database.models.user import User
from src.api.schemas.ingestion import IngestionJobResponse
from src.api.dependencies import get_current_active_user
from config.logger import logger

router = APIRouter(prefix="/upload/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=IngestionJobResponse)
def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get status of an ingestion job.
    
    Returns job details including:
    - status (pending, processing, completed, failed)
    - progress (processed_chunks / total_chunks)
    - error message if failed
    """
    # Get job
    job = db.query(IngestionJob).filter(
        IngestionJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check ownership via chat_type
    chat_type = db.query(ChatType).filter(ChatType.id == job.chat_type_id).first()
    if not chat_type or chat_type.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this job"
        )
    
    return job


@router.get("/", response_model=List[IngestionJobResponse])
def list_jobs(
    chat_type_id: UUID = None,
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List ingestion jobs with optional filtering.
    Only returns jobs for chat types owned by the current user.
    """
    query = db.query(IngestionJob).select_from(IngestionJob).join(ChatType, IngestionJob.chat_type_id == ChatType.id)
    
    # Filter by user ownership
    query = query.filter(ChatType.owner_id == current_user.id)
    
    if chat_type_id is not None:
        query = query.filter(IngestionJob.chat_type_id == chat_type_id)
    
    if status_filter is not None:
        query = query.filter(IngestionJob.status == status_filter)
    
    jobs = query.order_by(IngestionJob.created_at.desc()).offset(skip).limit(limit).all()
    return jobs


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a job record (only for completed or failed jobs).
    """
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check ownership via chat_type
    chat_type = db.query(ChatType).filter(ChatType.id == job.chat_type_id).first()
    if not chat_type or chat_type.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this job"
        )
    
    if job.status in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a job that is still running"
        )
    
    db.delete(job)
    db.commit()
    
    logger.info(f"Deleted job {job_id}")
