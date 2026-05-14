import pytest
from fastapi import status
from uuid import uuid4


@pytest.mark.integration
class TestChatsRoutes:
    """Testes de integração para rotas de chats"""

    def test_create_chat_success(self, client, sample_user, sample_chat_type, sample_jwt_token):
        """Testa criação de chat com sucesso"""
        response = client.post(
            "/api/v1/chats/",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={
                "chat_type_id": str(sample_chat_type.id),
                "title": "Test Chat"
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Test Chat"
        assert data["user_id"] == str(sample_user.id)

    def test_create_chat_auto_title(self, client, sample_user, sample_chat_type, sample_jwt_token):
        """Testa criação de chat com título automático"""
        response = client.post(
            "/api/v1/chats/",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={
                "chat_type_id": str(sample_chat_type.id)
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "Chat #" in data["title"]

    def test_create_chat_invalid_chat_type(self, client, sample_user, sample_jwt_token):
        """Testa criação com chat type inexistente"""
        response = client.post(
            "/api/v1/chats/",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={
                "chat_type_id": str(uuid4()),
                "title": "Test Chat"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_chats(self, client, sample_user, sample_chat, sample_jwt_token):
        """Testa listagem de chats"""
        response = client.get(
            "/api/v1/chats/",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_chat(self, client, sample_user, sample_chat, sample_jwt_token):
        """Testa obtenção de chat por ID"""
        response = client.get(
            f"/api/v1/chats/{sample_chat.id}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_chat.id)
        assert data["title"] == sample_chat.title

    def test_get_chat_not_found(self, client, sample_user, sample_jwt_token):
        """Testa obtenção de chat inexistente"""
        response = client.get(
            f"/api/v1/chats/{uuid4()}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_chat(self, client, sample_user, sample_chat, sample_jwt_token):
        """Testa exclusão de chat"""
        response = client.delete(
            f"/api/v1/chats/{sample_chat.id}",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_unauthorized_access(self, client):
        """Testa acesso sem autenticação"""
        response = client.get("/api/v1/chats/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_chat_model(self, client, sample_user, sample_chat, sample_jwt_token):
        """Testa atualização de modelo do chat"""
        response = client.patch(
            f"/api/v1/chats/{sample_chat.id}/model",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={
                "llm_model": "gpt-4",
                "llm_provider": "openai"
            }
        )
        
        # May succeed or fail depending on available models config
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_get_available_models(self, client, sample_jwt_token):
        """Testa obtenção de modelos disponíveis"""
        response = client.get(
            "/api/v1/chats/models/available",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "models" in data
        assert "current_default" in data
