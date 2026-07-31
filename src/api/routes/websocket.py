"""
WebSocket endpoint for real-time chat updates.
"""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from shared.database.session import get_db
from src.api.schemas.ingestion import IngestionJobResponse
from src.repositories.chat import ChatRepository
from src.repositories.ingestion_job import IngestionJobRepository
from src.repositories.user import UserRepository
from src.services.auth import auth_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}
        self._loop = None

    def get_event_loop(self):
        """Get or create the event loop."""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    async def connect(self, websocket: WebSocket, chat_id: str):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = set()
        self.active_connections[chat_id].add(websocket)
        logger.info(
            f"WebSocket connected for chat {chat_id}. Total connections: {len(self.active_connections[chat_id])}"
        )

    def disconnect(self, websocket: WebSocket, chat_id: str):
        if chat_id in self.active_connections:
            self.active_connections[chat_id].discard(websocket)
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]
            logger.info(
                f"WebSocket disconnected for chat {chat_id}. Remaining: {len(self.active_connections.get(chat_id, set()))}"
            )

    async def send_to_chat(self, chat_id: str, message: dict):
        """Send a message to all connected clients for a specific chat."""
        if chat_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[chat_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    disconnected.append(connection)

            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[chat_id].discard(conn)

            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]


manager = ConnectionManager()


@router.websocket("/ws/chats/{chat_id}")
async def websocket_endpoint(
    websocket: WebSocket, chat_id: str, token: str | None = None
):
    """WebSocket endpoint for real-time chat updates."""
    # Authenticate via token query param or cookie
    if not token:
        token = websocket.cookies.get("authToken")

    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        db: Session = next(get_db())
        user_repo = UserRepository(db)
        user = auth_service.get_current_user_from_token(token, user_repo)
        if user is None:
            await websocket.close(code=4001, reason="Invalid token")
            return

        # Verify chat ownership
        chat_repo = ChatRepository(db)
        chat = chat_repo.get_by_id(UUID(chat_id))
        if chat is None or chat.user_id != user.id:
            await websocket.close(code=4003, reason="Forbidden")
            return
    except Exception as e:
        logger.warning(f"WebSocket auth error for chat {chat_id}: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    finally:
        db.close()

    await manager.connect(websocket, chat_id)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message from chat {chat_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)
    except Exception as e:
        logger.error(f"WebSocket error for chat {chat_id}: {e}")
        manager.disconnect(websocket, chat_id)


def broadcast_chat_update(chat_id: str, update_type: str, data: dict):
    """Broadcast a chat update to all connected clients.

    This function can be called from background threads.

    Args:
        chat_id: The ID of the chat
        update_type: Type of update (e.g., 'title', 'message', 'status')
        data: The update data
    """
    message = {"type": update_type, "chat_id": chat_id, "data": data}

    # Try to get the running event loop
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.create_task(manager.send_to_chat(chat_id, message))
        else:
            # If loop exists but is not running, schedule the coroutine
            asyncio.run_coroutine_threadsafe(
                manager.send_to_chat(chat_id, message), loop
            )
    except RuntimeError:
        # No running event loop, create a new one
        try:
            loop = manager.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    manager.send_to_chat(chat_id, message), loop
                )
            else:
                # Run the coroutine in the new loop
                loop.run_until_complete(manager.send_to_chat(chat_id, message))
        except Exception as e:
            logger.error(f"Failed to broadcast WebSocket message: {e}")
    except Exception as e:
        logger.error(f"Failed to broadcast WebSocket message: {e}")


@router.websocket("/ws/jobs")
async def websocket_jobs_endpoint(websocket: WebSocket, token: str | None = None):
    """WebSocket endpoint for real-time job progress polling."""
    logger.info("Incoming WebSocket connection for /ws/jobs")

    # Authenticate via token query param or cookie
    if not token:
        token = websocket.cookies.get("authToken")

    if not token:
        logger.warning("WebSocket jobs connection rejected: Missing token")
        await websocket.close(code=4001, reason="Missing token")
        return

    db = None
    try:
        db = next(get_db())
        user_repo = UserRepository(db)
        user = auth_service.get_current_user_from_token(token, user_repo)
        if user is None:
            await websocket.close(code=4001, reason="Invalid token")
            return

        await websocket.accept()
        logger.info(f"WebSocket jobs connected for user {user.id}")

        job_repo = IngestionJobRepository(db)

        # Poll jobs for this user every 2 seconds
        while True:
            try:
                # Refresh session to see updates from worker
                db.expire_all()
                db.rollback()

                # We limit to 50 active jobs, which is plenty for frontend UI
                jobs = job_repo.get_by_user(user_id=user.id, skip=0, limit=50)

                # Serialize using Pydantic model
                jobs_data = [
                    IngestionJobResponse.model_validate(job).model_dump(mode="json")
                    for job in jobs
                ]

                await websocket.send_json(jobs_data)
                await asyncio.sleep(2.0)
            except WebSocketDisconnect:
                logger.info(f"WebSocket jobs disconnected for user {user.id}")
                break
            except Exception as e:
                logger.error(f"WebSocket jobs error during polling: {e}")
                await asyncio.sleep(2.0)  # avoid tight loop on DB error

    except Exception as e:
        logger.warning(f"WebSocket jobs auth error: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
    finally:
        if db:
            db.close()
