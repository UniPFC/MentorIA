from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest


@pytest.mark.unit
class TestWebsocketRoutes:
    """Testes unitários para rotas de websocket"""

    def test_connection_manager_disconnect(self):
        """Testa disconnect do ConnectionManager"""
        from src.api.routes.websocket import manager

        mock_ws = Mock()
        manager.active_connections["test_chat"] = {mock_ws}

        manager.disconnect(mock_ws, "test_chat")

        assert "test_chat" not in manager.active_connections

    def test_send_to_chat_with_disconnect(self):
        """Testa send_to_chat quando conexão falha"""
        import asyncio

        from src.api.routes.websocket import manager

        mock_ws1 = AsyncMock()
        mock_ws1.send_json.side_effect = Exception("Connection closed")

        mock_ws2 = AsyncMock()
        mock_ws2.send_json.return_value = None

        manager.active_connections["test_chat"] = {mock_ws1, mock_ws2}

        asyncio.run(manager.send_to_chat("test_chat", {"type": "test"}))

        # mock_ws2 should still be in connections, mock_ws1 removed
        assert mock_ws2 in manager.active_connections.get("test_chat", set())
        assert mock_ws1 not in manager.active_connections.get("test_chat", set())

    def test_broadcast_chat_update_with_running_loop(self):
        """Testa broadcast com loop rodando"""
        from src.api.routes.websocket import broadcast_chat_update, manager

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop

            with patch.object(manager, "send_to_chat", new=Mock()):
                broadcast_chat_update("test_chat", "title", {"title": "New Title"})

                mock_loop.is_running.assert_called_once()

    def test_broadcast_chat_update_no_loop(self):
        """Testa broadcast sem loop rodando"""
        from src.api.routes.websocket import broadcast_chat_update, manager

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_get_loop.side_effect = RuntimeError("No running event loop")

            with patch.object(manager, "get_event_loop") as mock_get_event_loop:
                mock_loop = Mock()
                mock_loop.is_running.return_value = False
                mock_get_event_loop.return_value = mock_loop

                with patch.object(manager, "send_to_chat", new=Mock()):
                    broadcast_chat_update("test_chat", "title", {"title": "New Title"})

                    mock_loop.run_until_complete.assert_called_once()

    def test_broadcast_chat_update_error(self):
        """Testa broadcast com erro no loop"""
        from src.api.routes.websocket import broadcast_chat_update, manager

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_get_loop.side_effect = RuntimeError("No running event loop")

            with patch.object(manager, "get_event_loop") as mock_get_event_loop:
                mock_get_event_loop.side_effect = Exception("Loop error")

                # Should not raise
                broadcast_chat_update("test_chat", "title", {"title": "New Title"})

    @pytest.mark.asyncio
    async def test_websocket_endpoint_no_token(self):
        """Testa websocket sem token"""
        from src.api.routes.websocket import websocket_endpoint

        mock_ws = Mock()
        mock_ws.cookies = {}
        mock_ws.close = AsyncMock()
        mock_ws.accept = AsyncMock()

        await websocket_endpoint(mock_ws, "test_chat", token=None)

        mock_ws.close.assert_called_once_with(code=4001, reason="Missing token")

    @pytest.mark.asyncio
    async def test_websocket_endpoint_invalid_token(self):
        """Testa websocket com token inválido"""
        from src.api.routes.websocket import websocket_endpoint

        mock_ws = Mock()
        mock_ws.cookies = {}
        mock_ws.close = AsyncMock()
        mock_ws.accept = AsyncMock()

        with patch("src.api.routes.websocket.auth_service") as mock_auth:
            mock_auth.get_current_user_from_token.return_value = None

            await websocket_endpoint(mock_ws, "test_chat", token="invalid")

            mock_ws.close.assert_called_once_with(code=4001, reason="Invalid token")

    @pytest.mark.asyncio
    async def test_websocket_endpoint_chat_not_owned(self):
        """Testa websocket com chat de outro usuário"""
        from src.api.routes.websocket import websocket_endpoint

        mock_ws = Mock()
        mock_ws.cookies = {}
        mock_ws.close = AsyncMock()
        mock_ws.accept = AsyncMock()
        user_id = uuid4()
        other_user_id = uuid4()

        mock_user = Mock()
        mock_user.id = user_id

        mock_chat = Mock()
        mock_chat.user_id = other_user_id

        with (
            patch("src.api.routes.websocket.auth_service") as mock_auth,
            patch("src.api.routes.websocket.ChatRepository") as mock_chat_repo,
        ):
            mock_auth.get_current_user_from_token.return_value = mock_user
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_chat
            mock_chat_repo.return_value = mock_repo

            await websocket_endpoint(mock_ws, str(uuid4()), token="valid_token")

            mock_ws.close.assert_called_once_with(code=4003, reason="Forbidden")

    @pytest.mark.asyncio
    async def test_websocket_endpoint_exception(self):
        """Testa websocket com exceção na autenticação"""
        from src.api.routes.websocket import websocket_endpoint

        mock_ws = Mock()
        mock_ws.cookies = {}
        mock_ws.close = AsyncMock()
        mock_ws.accept = AsyncMock()

        with patch("src.api.routes.websocket.auth_service") as mock_auth:
            mock_auth.get_current_user_from_token.side_effect = Exception("Auth error")

            await websocket_endpoint(mock_ws, "test_chat", token="valid_token")

            mock_ws.close.assert_called_once_with(
                code=4001, reason="Authentication failed"
            )
