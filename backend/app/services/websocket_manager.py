# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import json
import logging
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time collaboration"""
    
    def __init__(self):
        # Active connections grouped by room (conflict_id, project_id, etc.)
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
        # User mapping for connection tracking
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: Optional[int] = None):
        """Connect a WebSocket to a room"""
        await websocket.accept()
        
        async with self.lock:
            # Add to room
            if room_id not in self.active_connections:
                self.active_connections[room_id] = set()
            self.active_connections[room_id].add(websocket)
            
            # Add to user connections
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(websocket)
            
            # Store metadata
            self.connection_metadata[websocket] = {
                "room_id": room_id,
                "user_id": user_id,
                "connected_at": datetime.utcnow(),
                "last_activity": datetime.utcnow()
            }
        
        logger.info(f"WebSocket connected to room {room_id} (user: {user_id})")
        
        # Notify other users in the room about new connection
        if user_id:
            await self.broadcast_to_room(room_id, {
                "type": "user_joined",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }, exclude_websocket=websocket)
    
    def _disconnect_sync(self, websocket: WebSocket) -> tuple[Optional[str], Optional[int]]:
        """Synchronous disconnect method for thread-safe operations within lock"""
        metadata = self.connection_metadata.get(websocket)
        if not metadata:
            return None, None
        
        room_id = metadata["room_id"]
        user_id = metadata["user_id"]
        
        # Remove from room
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove metadata
        del self.connection_metadata[websocket]
        
        logger.info(f"WebSocket disconnected from room {room_id} (user: {user_id})")
        
        return room_id, user_id
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket from all rooms"""
        async with self.lock:
            room_id, user_id = self._disconnect_sync(websocket)
        
        # Notify other users in the room about disconnection (outside of lock)
        if user_id and room_id:
            await self.broadcast_to_room(room_id, {
                "type": "user_left",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
            # Update last activity
            async with self.lock:
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]["last_activity"] = datetime.utcnow()
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude_websocket: Optional[WebSocket] = None):
        """Broadcast a message to all connections in a room"""
        # Get connections to broadcast to (thread-safe)
        async with self.lock:
            if room_id not in self.active_connections:
                return
            connections_to_broadcast = list(self.active_connections[room_id])
        
        message_text = json.dumps(message)
        disconnected_connections = []
        
        for connection in connections_to_broadcast:
            if connection == exclude_websocket:
                continue
                
            try:
                await connection.send_text(message_text)
                # Update last activity
                async with self.lock:
                    if connection in self.connection_metadata:
                        self.connection_metadata[connection]["last_activity"] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error broadcasting to room {room_id}: {e}")
                disconnected_connections.append(connection)
        
        # Clean up disconnected connections (thread-safe)
        if disconnected_connections:
            async with self.lock:
                for connection in disconnected_connections:
                    self._disconnect_sync(connection)
    
    async def broadcast_to_user(self, user_id: int, message: dict):
        """Broadcast a message to all connections of a specific user"""
        # Get connections to broadcast to (thread-safe)
        async with self.lock:
            if user_id not in self.user_connections:
                return
            connections_to_broadcast = list(self.user_connections[user_id])
        
        message_text = json.dumps(message)
        disconnected_connections = []
        
        for connection in connections_to_broadcast:
            try:
                await connection.send_text(message_text)
                # Update last activity
                async with self.lock:
                    if connection in self.connection_metadata:
                        self.connection_metadata[connection]["last_activity"] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected_connections.append(connection)
        
        # Clean up disconnected connections (thread-safe)
        if disconnected_connections:
            async with self.lock:
                for connection in disconnected_connections:
                    self._disconnect_sync(connection)
    
    async def get_room_users(self, room_id: str) -> List[int]:
        """Get list of user IDs currently connected to a room"""
        async with self.lock:
            if room_id not in self.active_connections:
                return []
            
            users = set()
            for connection in self.active_connections[room_id]:
                metadata = self.connection_metadata.get(connection)
                if metadata and metadata["user_id"]:
                    users.add(metadata["user_id"])
            
            return list(users)
    
    async def get_connection_count(self, room_id: str) -> int:
        """Get number of active connections in a room"""
        async with self.lock:
            return len(self.active_connections.get(room_id, set()))
    
    async def get_user_connection_count(self, user_id: int) -> int:
        """Get number of active connections for a user"""
        async with self.lock:
            return len(self.user_connections.get(user_id, set()))
    
    async def is_user_online(self, user_id: int) -> bool:
        """Check if a user has any active connections"""
        async with self.lock:
            return user_id in self.user_connections and len(self.user_connections[user_id]) > 0
    
    async def send_typing_indicator(self, room_id: str, user_id: int, is_typing: bool):
        """Send typing indicator to room"""
        await self.broadcast_to_room(room_id, {
            "type": "typing_indicator",
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_user_presence(self, room_id: str, user_id: int, status: str):
        """Send user presence update to room"""
        await self.broadcast_to_room(room_id, {
            "type": "user_presence",
            "user_id": user_id,
            "status": status,  # 'online', 'away', 'busy', 'offline'
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def get_room_stats(self, room_id: str) -> Dict[str, Any]:
        """Get statistics for a room"""
        async with self.lock:
            if room_id not in self.active_connections:
                return {"active_connections": 0, "active_users": []}
            
            # Get users synchronously within the lock
            users = set()
            for connection in self.active_connections[room_id]:
                metadata = self.connection_metadata.get(connection)
                if metadata and metadata["user_id"]:
                    users.add(metadata["user_id"])
            
            return {
                "active_connections": len(self.active_connections[room_id]),
                "active_users": list(users)
            }
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global connection statistics"""
        async with self.lock:
            total_connections = sum(len(connections) for connections in self.active_connections.values())
            total_users = len(self.user_connections)
            
            return {
                "total_connections": total_connections,
                "total_users": total_users,
                "active_rooms": len(self.active_connections),
                "rooms": {room_id: len(connections) for room_id, connections in self.active_connections.items()}
            }
    
    async def cleanup_stale_connections(self, max_idle_minutes: int = 60):
        """Clean up connections that have been idle for too long"""
        cutoff_time = datetime.utcnow().timestamp() - (max_idle_minutes * 60)
        stale_connections = []
        
        # Find stale connections (thread-safe)
        async with self.lock:
            for websocket, metadata in self.connection_metadata.items():
                last_activity = metadata["last_activity"].timestamp()
                if last_activity < cutoff_time:
                    stale_connections.append((websocket, metadata["room_id"]))
        
        # Clean up stale connections (outside of lock to avoid deadlock)
        for websocket, room_id in stale_connections:
            logger.info(f"Cleaning up stale connection from room {room_id}")
            await self.disconnect(websocket)
            try:
                await websocket.close()
            except:
                pass


# Global connection manager instance
connection_manager = ConnectionManager()


class CollaborationManager:
    """High-level manager for collaboration features"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def notify_comment_added(self, room_id: str, comment_data: dict, exclude_user_id: Optional[int] = None):
        """Notify room about new comment"""
        message = {
            "type": "comment_added",
            "data": comment_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Find WebSocket to exclude based on user ID (thread-safe)
        exclude_websocket = None
        if exclude_user_id:
            async with self.connection_manager.lock:
                if room_id in self.connection_manager.active_connections:
                    for ws in self.connection_manager.active_connections[room_id]:
                        metadata = self.connection_manager.connection_metadata.get(ws)
                        if metadata and metadata["user_id"] == exclude_user_id:
                            exclude_websocket = ws
                            break
        
        await self.connection_manager.broadcast_to_room(room_id, message, exclude_websocket)
    
    async def notify_annotation_added(self, room_id: str, annotation_data: dict, exclude_user_id: Optional[int] = None):
        """Notify room about new annotation"""
        message = {
            "type": "annotation_added",
            "data": annotation_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Find WebSocket to exclude based on user ID (thread-safe)
        exclude_websocket = None
        if exclude_user_id:
            async with self.connection_manager.lock:
                if room_id in self.connection_manager.active_connections:
                    for ws in self.connection_manager.active_connections[room_id]:
                        metadata = self.connection_manager.connection_metadata.get(ws)
                        if metadata and metadata["user_id"] == exclude_user_id:
                            exclude_websocket = ws
                            break
        
        await self.connection_manager.broadcast_to_room(room_id, message, exclude_websocket)
    
    async def notify_conflict_status_changed(self, room_id: str, status_data: dict):
        """Notify room about conflict status change"""
        message = {
            "type": "conflict_status_changed",
            "data": status_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.broadcast_to_room(room_id, message)
    
    async def notify_solution_added(self, room_id: str, solution_data: dict, exclude_user_id: Optional[int] = None):
        """Notify room about new solution"""
        message = {
            "type": "solution_added",
            "data": solution_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Find WebSocket to exclude based on user ID (thread-safe)
        exclude_websocket = None
        if exclude_user_id:
            async with self.connection_manager.lock:
                if room_id in self.connection_manager.active_connections:
                    for ws in self.connection_manager.active_connections[room_id]:
                        metadata = self.connection_manager.connection_metadata.get(ws)
                        if metadata and metadata["user_id"] == exclude_user_id:
                            exclude_websocket = ws
                            break
        
        await self.connection_manager.broadcast_to_room(room_id, message, exclude_websocket)


# Global collaboration manager instance
collaboration_manager = CollaborationManager(connection_manager)