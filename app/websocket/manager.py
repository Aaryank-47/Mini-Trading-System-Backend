"""
WebSocket connection manager
Handles WebSocket connections for real-time updates
"""
from fastapi import WebSocket
from typing import Dict, Set
from app.schemas import OrderExecutedMessage
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections per user"""
    
    def __init__(self):
        # Store active connections: {user_id: set(WebSocket)}
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, user_id: int, websocket: WebSocket):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"✓ WebSocket connected for user {user_id}")
    
    async def disconnect(self, user_id: int, websocket: WebSocket):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Clean up empty user sets
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            logger.info(f"✓ WebSocket disconnected for user {user_id}")
    
    async def broadcast_to_user(self, user_id: int, message: dict):
        """Send message to all connections of a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.add(websocket)
            
            # Remove disconnected connections
            self.active_connections[user_id] -= disconnected
    
    async def broadcast_to_all(self, message: dict):
        """Send message to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.broadcast_to_user(user_id, message)
    
    def get_active_users(self) -> list:
        """Get list of users with active connections"""
        return list(self.active_connections.keys())
    
    def get_connection_count(self, user_id: int) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager"""
    return connection_manager
