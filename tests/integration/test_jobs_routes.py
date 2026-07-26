from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import status

from shared.database.models.ingestion_job import IngestionJob, IngestionStatus


@pytest.mark.integration
class TestJobsRoutes:
    """Testes de integração para rotas de jobs"""

    def test_get_job_status(
        self, client, sample_user, sample_chat_type, sample_jwt_token, db_session
    ):
        """Testa obtenção de status de job existente"""
        # Create a job
        job = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="test.pdf",
            status=IngestionStatus.COMPLETED,
            total_chunks=10,
            processed_chunks=10,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(
            f"/api/v1/upload/jobs/{job.id}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(job.id)
        assert data["status"] == "completed"

    def test_get_job_status_not_found(self, client, sample_user, sample_jwt_token):
        """Testa obtenção de status de job inexistente"""
        response = client.get(
            f"/api/v1/upload/jobs/{uuid4()}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_job_status_forbidden(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa obtenção de status de job de outro usuário"""
        from shared.database.models.chat_type import ChatType
        from shared.database.models.user import User

        # Create another user and their chat type
        other_user = User(
            id=uuid4(),
            username="otheruser",
            email="other@example.com",
            password_hash="hashed",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db_session.add(other_user)
        db_session.commit()

        chat_type = ChatType(
            id=uuid4(),
            name="Other Type",
            description="Test",
            owner_id=other_user.id,
            collection_name="other_test",
            created_at=datetime.now(UTC),
        )
        db_session.add(chat_type)
        db_session.commit()

        job = IngestionJob(
            id=uuid4(),
            chat_type_id=chat_type.id,
            filename="test.pdf",
            status=IngestionStatus.COMPLETED,
            total_chunks=10,
            processed_chunks=10,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(
            f"/api/v1/upload/jobs/{job.id}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_jobs(
        self, client, sample_user, sample_chat_type, sample_jwt_token, db_session
    ):
        """Testa listagem de jobs"""
        job = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="test.pdf",
            status=IngestionStatus.COMPLETED,
            total_chunks=10,
            processed_chunks=10,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(
            "/api/v1/upload/jobs/",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_delete_job(
        self, client, sample_user, sample_chat_type, sample_jwt_token, db_session
    ):
        """Testa exclusão de job"""
        job = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="test.pdf",
            status=IngestionStatus.COMPLETED,
            total_chunks=10,
            processed_chunks=10,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        response = client.delete(
            f"/api/v1/upload/jobs/{job.id}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_job_running(
        self, client, sample_user, sample_chat_type, sample_jwt_token, db_session
    ):
        """Testa exclusão de job em andamento"""
        job = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="test.pdf",
            status=IngestionStatus.PROCESSING,
            total_chunks=10,
            processed_chunks=5,
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()

        response = client.delete(
            f"/api/v1/upload/jobs/{job.id}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot delete" in response.json()["detail"]

    def test_unauthorized_access(self, client):
        """Testa acesso sem autenticação"""
        response = client.get("/api/v1/upload/jobs/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
