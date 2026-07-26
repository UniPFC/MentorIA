from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status


@pytest.mark.integration
class TestChatTypesRoutes:
    """Testes de integração para rotas de chat types"""

    def test_create_chat_type_success(self, client, sample_user, sample_jwt_token):
        """Testa criação de chat type com sucesso"""
        with patch('src.api.routes.chat_types.QdrantManager'):
            response = client.post(
                "/api/v1/chat-types/",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={
                    "name": "Test Chat Type Integration",
                    "description": "A test chat type",
                    "is_public": False
                }
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["name"] == "Test Chat Type Integration"
            assert data["description"] == "A test chat type"

    def test_create_chat_type_duplicate_name(self, client, sample_user, sample_chat_type, sample_jwt_token):
        """Testa criação com nome duplicado"""
        response = client.post(
            "/api/v1/chat-types/",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={
                "name": sample_chat_type.name,
                "description": "Duplicate",
                "is_public": False
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_list_chat_types(self, client, sample_user, sample_chat_type, sample_jwt_token):
        """Testa listagem de chat types"""
        response = client.get(
            "/api/v1/chat-types/",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "chat_types" in data

    def test_get_chat_type(self, client, sample_user, sample_chat_type, sample_jwt_token):
        """Testa obtenção de chat type por ID"""
        response = client.get(
            f"/api/v1/chat-types/{sample_chat_type.id}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_chat_type.id)
        assert data["name"] == sample_chat_type.name

    def test_get_chat_type_not_found(self, client, sample_user, sample_jwt_token):
        """Testa obtenção de chat type inexistente"""
        response = client.get(
            f"/api/v1/chat-types/{uuid4()}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_chat_type(self, client, sample_user, sample_chat_type, sample_jwt_token):
        """Testa atualização de chat type"""
        response = client.patch(
            f"/api/v1/chat-types/{sample_chat_type.id}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={
                "name": "Updated Name",
                "description": "Updated description"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_delete_chat_type(self, client, sample_user, sample_jwt_token):
        """Testa exclusão de chat type"""
        # Primeiro cria um chat type para deletar
        with patch('src.api.routes.chat_types.QdrantManager'):
            create_response = client.post(
                "/api/v1/chat-types/",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={
                    "name": "To Delete",
                    "description": "Will be deleted",
                    "is_public": False
                }
            )

            assert create_response.status_code == status.HTTP_201_CREATED
            chat_type_id = create_response.json()["id"]

        with patch('src.api.routes.chat_types.QdrantManager'):
            response = client.delete(
                f"/api/v1/chat-types/{chat_type_id}",
                headers={"Authorization": f"Bearer {sample_jwt_token}"}
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_unauthorized_access(self, client):
        """Testa acesso sem autenticação"""
        response = client.get("/api/v1/chat-types/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
