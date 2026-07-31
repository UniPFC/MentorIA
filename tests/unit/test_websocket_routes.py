import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.api.routes.websocket import (
    broadcast_chat_update,
    manager,
    websocket_jobs_endpoint,
)


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


@pytest.mark.asyncio
async def test_send_to_chat_del_active_connections():
    mock_ws = AsyncMock()
    mock_ws.send_json.side_effect = Exception("Fail")
    manager.active_connections["del_chat"] = {mock_ws}

    await manager.send_to_chat("del_chat", {"msg": "hi"})
    assert "del_chat" not in manager.active_connections


@pytest.mark.asyncio
async def test_websocket_endpoint_loop_exception():
    from src.api.routes.websocket import websocket_endpoint

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = Exception("Random error")
    mock_ws.cookies = {"authToken": "valid"}

    with (
        patch("src.api.routes.websocket.auth_service") as mock_auth,
        patch("src.api.routes.websocket.ChatRepository") as mock_repo,
        patch("src.api.routes.websocket.get_db") as mock_get_db,
    ):
        mock_get_db.return_value = iter([Mock()])
        mock_auth.get_current_user_from_token.return_value = Mock(id="user1")
        mock_repo.return_value.get_by_id.return_value = Mock(user_id="user1")

        await websocket_endpoint(mock_ws, "chat1", token="valid")
        assert "chat1" not in manager.active_connections


def test_broadcast_chat_update_loop_not_running():
    with (
        patch("asyncio.get_running_loop") as mock_get_loop,
        patch.object(manager, "send_to_chat", new_callable=Mock) as mock_send,
        patch("asyncio.run_coroutine_threadsafe") as mock_run_coroutine,
    ):
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_get_loop.return_value = mock_loop

        broadcast_chat_update("chat", "type", {})
        mock_run_coroutine.assert_called_once()


def test_broadcast_chat_update_runtime_error_loop_running():
    with (
        patch("asyncio.get_running_loop", side_effect=RuntimeError),
        patch.object(manager, "get_event_loop") as mock_get_event_loop,
        patch.object(manager, "send_to_chat", new_callable=Mock) as mock_send,
        patch("asyncio.run_coroutine_threadsafe") as mock_run_coroutine,
    ):
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_event_loop.return_value = mock_loop

        broadcast_chat_update("chat", "type", {})
        mock_run_coroutine.assert_called_once()


def test_broadcast_chat_update_outer_exception():
    with (
        patch("asyncio.get_running_loop", side_effect=Exception("Outer error")),
        patch.object(manager, "send_to_chat", new_callable=Mock) as mock_send,
    ):
        # Should not raise exception
        broadcast_chat_update("chat", "type", {})


@pytest.mark.asyncio
async def test_websocket_jobs_endpoint_no_token():
    mock_ws = AsyncMock()
    mock_ws.cookies = {}
    await websocket_jobs_endpoint(mock_ws, token=None)
    mock_ws.close.assert_called_with(code=4001, reason="Missing token")


@pytest.mark.asyncio
async def test_websocket_jobs_endpoint_invalid_token():
    mock_ws = AsyncMock()
    mock_ws.cookies = {"authToken": "invalid"}
    with (
        patch("src.api.routes.websocket.get_db") as mock_get_db,
        patch("src.api.routes.websocket.auth_service") as mock_auth,
    ):
        mock_get_db.return_value = iter([Mock()])
        mock_auth.get_current_user_from_token.return_value = None
        await websocket_jobs_endpoint(mock_ws)
        mock_ws.close.assert_called_with(code=4001, reason="Invalid token")


@pytest.mark.asyncio
async def test_websocket_jobs_endpoint_auth_exception():
    mock_ws = AsyncMock()
    mock_ws.cookies = {"authToken": "valid"}
    with patch("src.api.routes.websocket.get_db") as mock_get_db:
        mock_get_db.side_effect = Exception("DB Error")
        await websocket_jobs_endpoint(mock_ws)
        mock_ws.close.assert_called_with(code=4001, reason="Authentication failed")


@pytest.mark.asyncio
async def test_websocket_jobs_endpoint_polling():
    mock_ws = AsyncMock()
    mock_ws.cookies = {"authToken": "valid"}

    with (
        patch("src.api.routes.websocket.get_db") as mock_get_db,
        patch("src.api.routes.websocket.auth_service") as mock_auth,
        patch("src.api.routes.websocket.IngestionJobRepository") as mock_job_repo,
        patch(
            "src.api.routes.websocket.asyncio.sleep",
            side_effect=[None, asyncio.CancelledError],
        ),
    ):
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])
        mock_auth.get_current_user_from_token.return_value = Mock(id="user1")

        mock_job = Mock()
        mock_job.status = "processing"
        mock_job_repo.return_value.get_by_user.return_value = [mock_job]

        from starlette.websockets import WebSocketDisconnect

        mock_ws.send_json.side_effect = [None, WebSocketDisconnect()]

        with patch("src.api.routes.websocket.IngestionJobResponse") as mock_response:
            mock_response.model_validate.return_value.model_dump.return_value = {
                "id": "1"
            }
            await websocket_jobs_endpoint(mock_ws, token="valid")

        mock_ws.send_json.assert_called()
        assert mock_ws.send_json.call_count == 2


@pytest.mark.asyncio
async def test_websocket_jobs_endpoint_disconnect():
    from fastapi import WebSocketDisconnect

    mock_ws = AsyncMock()
    mock_ws.cookies = {"authToken": "valid"}
    mock_ws.send_json.side_effect = WebSocketDisconnect()

    with (
        patch("src.api.routes.websocket.get_db") as mock_get_db,
        patch("src.api.routes.websocket.auth_service") as mock_auth,
        patch("src.api.routes.websocket.IngestionJobRepository") as mock_job_repo,
    ):
        mock_get_db.return_value = iter([Mock()])
        mock_auth.get_current_user_from_token.return_value = Mock(id="user1")

        await websocket_jobs_endpoint(mock_ws)
        # Should exit loop cleanly


@pytest.mark.asyncio
async def test_websocket_jobs_endpoint_polling_exception():
    mock_ws = AsyncMock()
    mock_ws.cookies = {"authToken": "valid"}
    mock_ws.send_json.side_effect = Exception("Unexpected error")

    with (
        patch("src.api.routes.websocket.get_db") as mock_get_db,
        patch("src.api.routes.websocket.auth_service") as mock_auth,
        patch("src.api.routes.websocket.IngestionJobRepository") as mock_job_repo,
        patch(
            "src.api.routes.websocket.asyncio.sleep",
            side_effect=[None, asyncio.CancelledError],
        ),
    ):
        mock_get_db.return_value = iter([Mock()])
        mock_auth.get_current_user_from_token.return_value = Mock(id="user1")

        try:
            await websocket_jobs_endpoint(mock_ws)
        except asyncio.CancelledError:
            pass
