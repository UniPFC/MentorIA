import pytest
from unittest.mock import patch
from fastapi import status
from uuid import uuid4
from io import BytesIO


@pytest.mark.integration
class TestUploadRoutes:
    """Testes de integração para rotas de upload"""

    def test_upload_file_invalid_format(self, client, sample_user, sample_jwt_token):
        """Testa upload com formato inválido"""
        response = client.post(
            "/api/v1/upload/chat-type",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            data={
                "name": "Test Type"
            },
            files={
                "file": ("test.txt", BytesIO(b"invalid content"), "text/plain")
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_file_missing_name(self, client, sample_user, sample_jwt_token):
        """Testa upload sem nome - falha na validação do Form antes de carregar modelos"""
        with patch('src.api.routes.upload.settings') as mock_settings:
            mock_settings.ALLOWED_EXTENSIONS = [".xlsx", ".csv"]
            mock_settings.EMBEDDING_PROVIDER = "remote"
            mock_settings.EMBEDDING_REMOTE_MODEL = "text-embedding-ada-002"
            mock_settings.EMBEDDING_REMOTE_PROVIDER = "openai"
            
            response = client.post(
                "/api/v1/upload/chat-type",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                data={},
                files={
                    "file": ("test.xlsx", BytesIO(b"fake excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                }
            )
            
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_CONTENT, status.HTTP_400_BAD_REQUEST]

    def test_upload_file_duplicate_name(self, client, sample_user, sample_chat_type, sample_jwt_token):
        """Testa upload com nome duplicado"""
        with patch('src.api.routes.upload.settings') as mock_settings:
            mock_settings.ALLOWED_EXTENSIONS = [".xlsx", ".csv"]
            mock_settings.EMBEDDING_PROVIDER = "remote"
            mock_settings.EMBEDDING_REMOTE_MODEL = "text-embedding-ada-002"
            mock_settings.EMBEDDING_REMOTE_PROVIDER = "openai"
            
            response = client.post(
                "/api/v1/upload/chat-type",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                data={
                    "name": sample_chat_type.name
                },
                files={
                    "file": ("test.xlsx", BytesIO(b"fake excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                }
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "already exists" in response.json()["detail"]

    def test_unauthorized_access(self, client):
        """Testa acesso sem autenticação"""
        response = client.post("/api/v1/upload/chat-type")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
