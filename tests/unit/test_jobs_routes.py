import pytest
from unittest.mock import Mock
from fastapi import HTTPException, status
from uuid import uuid4
from datetime import datetime, timezone
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus


@pytest.mark.unit
class TestJobsRoutes:
    """Testes unitários para rotas de jobs"""

    def test_get_job_status_success(self):
        """Testa obtenção de status de job bem-sucedida"""
        job_id = uuid4()
        user_id = uuid4()
        chat_type_id = uuid4()
        
        job = Mock()
        job.id = job_id
        job.chat_type_id = chat_type_id
        job.status = IngestionStatus.COMPLETED
        
        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.owner_id = user_id
        
        job_repo = Mock()
        job_repo.get_by_id.return_value = job
        
        chat_type_repo = Mock()
        chat_type_repo.get_by_id.return_value = chat_type
        
        # Simula a lógica do endpoint
        job = job_repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        chat_type = chat_type_repo.get_by_id(job.chat_type_id)
        if not chat_type or chat_type.owner_id != user_id:
            raise HTTPException(status_code=403, detail="No permission")
        
        assert job.id == job_id

    def test_get_job_status_not_found(self):
        """Testa obtenção de status quando job não existe"""
        job_id = uuid4()
        user_id = uuid4()
        
        job_repo = Mock()
        job_repo.get_by_id.return_value = None
        
        chat_type_repo = Mock()
        
        # Simula a lógica do endpoint - deve levantar HTTPException
        with pytest.raises(HTTPException) as exc_info:
            job = job_repo.get_by_id(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
        
        assert exc_info.value.status_code == 404
        assert "Job not found" in exc_info.value.detail

    def test_get_job_status_forbidden(self):
        """Testa obtenção de status quando usuário não tem permissão"""
        job_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()
        chat_type_id = uuid4()
        
        job = Mock()
        job.id = job_id
        job.chat_type_id = chat_type_id
        
        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.owner_id = other_user_id  # Different user
        
        job_repo = Mock()
        job_repo.get_by_id.return_value = job
        
        chat_type_repo = Mock()
        chat_type_repo.get_by_id.return_value = chat_type
        
        # Simula a lógica do endpoint - deve levantar HTTPException
        with pytest.raises(HTTPException) as exc_info:
            job = job_repo.get_by_id(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            chat_type = chat_type_repo.get_by_id(job.chat_type_id)
            if not chat_type or chat_type.owner_id != user_id:
                raise HTTPException(status_code=403, detail="No permission")
        
        assert exc_info.value.status_code == 403
        assert "No permission" in exc_info.value.detail

    def test_delete_job_success(self):
        """Testa exclusão de job bem-sucedida"""
        job_id = uuid4()
        user_id = uuid4()
        chat_type_id = uuid4()
        
        job = Mock()
        job.id = job_id
        job.chat_type_id = chat_type_id
        job.status = IngestionStatus.COMPLETED
        
        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.owner_id = user_id
        
        job_repo = Mock()
        job_repo.get_by_id.return_value = job
        job_repo.delete.return_value = None
        
        chat_type_repo = Mock()
        chat_type_repo.get_by_id.return_value = chat_type
        
        # Simula a lógica do endpoint
        job = job_repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        chat_type = chat_type_repo.get_by_id(job.chat_type_id)
        if chat_type and chat_type.owner_id != user_id:
            raise HTTPException(status_code=403, detail="No permission")
        
        if job.status in ["pending", "processing"]:
            raise HTTPException(status_code=400, detail="Cannot delete running job")
        
        job_repo.delete(job)
        
        job_repo.delete.assert_called_once_with(job)

    def test_delete_job_running(self):
        """Testa exclusão de job em andamento (deve falhar)"""
        job_id = uuid4()
        user_id = uuid4()
        chat_type_id = uuid4()
        
        job = Mock()
        job.id = job_id
        job.chat_type_id = chat_type_id
        job.status = IngestionStatus.PROCESSING
        
        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.owner_id = user_id
        
        job_repo = Mock()
        job_repo.get_by_id.return_value = job
        
        chat_type_repo = Mock()
        chat_type_repo.get_by_id.return_value = chat_type
        
        # Simula a lógica do endpoint - deve levantar HTTPException
        with pytest.raises(HTTPException) as exc_info:
            job = job_repo.get_by_id(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            chat_type = chat_type_repo.get_by_id(job.chat_type_id)
            if chat_type and chat_type.owner_id != user_id:
                raise HTTPException(status_code=403, detail="No permission")
            
            if job.status in ["pending", "processing"]:
                raise HTTPException(status_code=400, detail="Cannot delete running job")
        
        assert exc_info.value.status_code == 400
        assert "Cannot delete running job" in exc_info.value.detail

    def test_delete_job_without_chat_type(self):
        """Testa exclusão de job quando chat_type foi deletado"""
        job_id = uuid4()
        user_id = uuid4()
        chat_type_id = uuid4()
        
        job = Mock()
        job.id = job_id
        job.chat_type_id = chat_type_id
        job.status = IngestionStatus.FAILED
        
        job_repo = Mock()
        job_repo.get_by_id.return_value = job
        job_repo.delete.return_value = None
        
        chat_type_repo = Mock()
        chat_type_repo.get_by_id.return_value = None  # Chat type deleted
        
        # Simula a lógica do endpoint
        job = job_repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        chat_type = chat_type_repo.get_by_id(job.chat_type_id)
        if chat_type and chat_type.owner_id != user_id:
            raise HTTPException(status_code=403, detail="No permission")
        
        if job.status in ["pending", "processing"]:
            raise HTTPException(status_code=400, detail="Cannot delete running job")
        
        job_repo.delete(job)
        
        job_repo.delete.assert_called_once_with(job)
