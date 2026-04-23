"""WebSocket API routes."""
import logging

from fastapi import APIRouter, Depends, Query, WebSocket, status
from jose import JWTError, jwt

from app.config import get_settings
from app.database import get_db
from app.services.user_service import UserService
from app.websocket import connection_manager

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    user_id: int,
    websocket: WebSocket,
    token: str = Query(None),
    db=Depends(get_db),
):
    """WebSocket endpoint for user-scoped real-time updates."""
    try:
        user = UserService.get_user(db, user_id)
        if not user:
            logger.warning(f"WebSocket connection rejected: User {user_id} not found")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return

        if token:
            try:
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                token_user_id = payload.get("sub")
                if not token_user_id or int(token_user_id) != user_id:
                    logger.warning(
                        f"WebSocket token mismatch: Token user {token_user_id} != {user_id}"
                    )
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason="Token mismatch",
                    )
                    return
            except JWTError as exc:
                logger.warning(f"Invalid JWT token for user {user_id}: {exc}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
    except Exception as exc:
        logger.error(f"WebSocket auth error for user {user_id}: {exc}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return

    await connection_manager.connect(user_id, websocket)
    logger.info(f"WebSocket connected: user_id={user_id}")

    try:
        while True:
            data = await websocket.receive_text()
            if data:
                logger.debug(f"Message from user {user_id}: {data}")
    except Exception as exc:
        logger.info(f"WebSocket error for user {user_id}: {exc}")
    finally:
        await connection_manager.disconnect(user_id, websocket)
        logger.info(f"WebSocket disconnected: user_id={user_id}")
