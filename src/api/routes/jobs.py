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
from src.api.dependencies import (
    get_current_active_user,
    get_ingestion_job_repo,
    get_chat_type_repo
)
from src.repositories.ingestion_job import IngestionJobRepository
from src.repositories.chat_type import ChatTypeRepository
from config.logger import logger

router = APIRouter(prefix="/upload/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=IngestionJobResponse)
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    job_repo: IngestionJobRepository = Depends(get_ingestion_job_repo),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo)
):
    """
    Get status of an ingestion job.
    
    Returns job details including:
    - status (pending, processing, completed, failed)
    - progress (processed_chunks / total_chunks)
    - error message if failed
    """
    
    job = job_repo.get_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check ownership via chat_type
    chat_type = chat_type_repo.get_by_id(job.chat_type_id)
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
    current_user: User = Depends(get_current_active_user),
    job_repo: IngestionJobRepository = Depends(get_ingestion_job_repo)
):
    """
    List ingestion jobs with optional filtering.
    Only returns jobs for chat types owned by the current user.
    """
    jobs = job_repo.get_by_user(
        user_id=current_user.id,
        chat_type_id=chat_type_id,
        skip=skip,
        limit=limit
    )
    
    if status_filter is not None:
        jobs = [job for job in jobs if job.status == status_filter]
    
    return jobs


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    job_repo: IngestionJobRepository = Depends(get_ingestion_job_repo),
    chat_type_repo: ChatTypeRepository = Depends(get_chat_type_repo)
):
    """
    Delete a job record (only for completed or failed jobs).
    """
    
    job = job_repo.get_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check ownership via chat_type (if it still exists)
    # If chat_type was deleted due to ingestion failure, we still allow deletion of the job
    chat_type = chat_type_repo.get_by_id(job.chat_type_id)
    if chat_type and chat_type.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this job"
        )
    
    if job.status in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a job that is still running"
        )
    
    job_repo.delete(job)
    
    logger.info(f"Deleted job {job_id}")
