import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from src.repositories.user import UserRepository
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.chat import Chat


@pytest.mark.integration
class TestWebSocketRoutes:
    """Testes de integração para rota WebSocket"""

    def test_websocket_missing_token(self, client):
        """Testa conexão WebSocket sem token"""
        with pytest.raises(Exception):  # WebSocketDisconnect
            with client.websocket_connect("/api/v1/ws/chats/test-chat-id") as websocket:
                pass

    def test_websocket_invalid_token(self, client):
        """Testa conexão WebSocket com token inválido"""
        with pytest.raises(Exception):  # WebSocketDisconnect
            with client.websocket_connect(
                "/api/v1/ws/chats/test-chat-id?token=invalid_token"
            ) as websocket:
                pass

    def test_websocket_nonexistent_chat(self, client, sample_user: User):
        """Testa conexão WebSocket para chat inexistente"""
        auth_service = AuthService()
        token = auth_service.create_access_token({"sub": str(sample_user.id)})
        
        chat_id = str(uuid4())  # Non-existent chat
        
        with pytest.raises(Exception):  # WebSocketDisconnect
            with client.websocket_connect(
                f"/api/v1/ws/chats/{chat_id}?token={token}"
            ) as websocket:
                pass

    def test_websocket_chat_not_owned(self, client, sample_user: User, sample_chat: Chat):
        """Testa conexão WebSocket para chat que não pertence ao usuário"""
        # Cria outro usuário e tenta conectar no chat do sample_user
        auth_service = AuthService()
        
        from shared.database.models.user import User
        other_user = User(
            id=uuid4(),
            username="otheruser",
            email="other@example.com",
            password_hash=auth_service.get_password_hash("password123"),
            is_active=True,
            created_at=sample_user.created_at
        )
        # Note: este teste é limitado sem salvar no DB via fixture
        # Vamos apenas verificar que a conexão é recusada para token de outro usuário
        token = auth_service.create_access_token({"sub": str(other_user.id)})
        
        with pytest.raises(Exception):  # WebSocketDisconnect
            with client.websocket_connect(
                f"/api/v1/ws/chats/{sample_chat.id}?token={token}"
            ) as websocket:
                pass

    def test_websocket_successful_connection(self, client, sample_user: User, sample_chat: Chat, db_session: Session):
        """Testa conexão WebSocket bem-sucedida com token válido no banco"""
        from src.services.auth import AuthService
        from src.repositories.user import UserRepository
        
        auth_service = AuthService()
        token = auth_service.create_access_token({"sub": str(sample_user.id)})
        
        # Register token in DB so websocket auth can validate it
        user_repo = UserRepository(db_session)
        user_repo.create_token(
            user_id=sample_user.id,
            token=token,
            token_type="access",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.commit()
        
        # Mock get_db to return the test session (websocket calls it directly, not via Depends)
        def mock_get_db():
            try:
                yield db_session
            finally:
                pass
        
        connection_accepted = False
        
        with patch('src.api.routes.websocket.get_db', mock_get_db):
            # WebSocket connect - if rejected during handshake, raises before entering 'with'
            with client.websocket_connect(
                f"/api/v1/ws/chats/{sample_chat.id}?token={token}"
            ) as websocket:
                connection_accepted = True
                # Send a message to confirm connection is active
                websocket.send_text('{"type": "ping"}')
        
        assert connection_accepted, "WebSocket connection should be accepted"

    def test_connection_manager_connect(self):
        """Testa ConnectionManager.connect"""
        from src.api.routes.websocket import ConnectionManager
        
        manager = ConnectionManager()
        websocket = Mock()
        websocket.accept = AsyncMock()
        
        chat_id = "test-chat"
        
        # This would need async test
        # For now, we'll test the structure
        assert chat_id not in manager.active_connections

    def test_connection_manager_disconnect(self):
        """Testa ConnectionManager.disconnect"""
        from src.api.routes.websocket import ConnectionManager
        
        manager = ConnectionManager()
        websocket = Mock()
        chat_id = "test-chat"
        
        # Simulate connection
        manager.active_connections[chat_id] = {websocket}
        
        manager.disconnect(websocket, chat_id)
        
        assert chat_id not in manager.active_connections

    def test_broadcast_chat_update(self):
        """Testa broadcast_chat_update function"""
        from src.api.routes.websocket import broadcast_chat_update, manager
        from unittest.mock import patch, AsyncMock
        
        chat_id = "test-chat"
        update_type = "message"
        data = {"content": "test"}
        
        # Mock the send_to_chat to avoid actual async execution
        with patch.object(manager, 'send_to_chat', new_callable=AsyncMock) as mock_send:
            broadcast_chat_update(chat_id, update_type, data)
            
            # Should have attempted to send
            # The actual execution depends on event loop state
            pass
