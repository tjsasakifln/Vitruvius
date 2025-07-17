# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
from pydantic import BaseModel, ValidationError, validator
import logging

logger = logging.getLogger(__name__)

from ...db.database import get_db
from ...auth.dependencies import get_current_active_user
from ...db.models.project import User, Project, Conflict
from ...db.models.collaboration import (
    Comment, CommentAttachment, Annotation, ActivityLog, 
    ConflictAssignment, WorkflowState, Notification, ConflictWatch
)
from ...services.websocket_manager import connection_manager, collaboration_manager

router = APIRouter(prefix="/collaboration", tags=["collaboration"])

# WebSocket message validation schemas
class AnnotationUpdateData(BaseModel):
    annotation_id: Optional[int] = None
    position: Optional[Dict[str, Any]] = None
    visual_data: Optional[Dict[str, Any]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        extra = "allow"

class TypingIndicatorData(BaseModel):
    is_typing: bool
    
class PresenceData(BaseModel):
    status: str
    
class WebSocketMessage(BaseModel):
    type: str
    data: Optional[Dict[str, Any]] = None
    is_typing: Optional[bool] = None
    status: Optional[str] = None
    
    class Config:
        max_anystr_length = 10000  # Limit string length
        
    @validator('type')
    def validate_message_type(cls, v):
        allowed_types = ['typing', 'presence', 'ping', 'annotation_update']
        if v not in allowed_types:
            raise ValueError(f'Invalid message type: {v}. Allowed types: {allowed_types}')
        return v

# File upload directory
UPLOAD_DIR = "/app/uploads/attachments"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.websocket("/ws/conflict/{conflict_id}")
async def websocket_endpoint(websocket: WebSocket, conflict_id: int, user_id: Optional[int] = None):
    """WebSocket endpoint for real-time collaboration on conflicts"""
    room_id = f"conflict_{conflict_id}"
    
    await connection_manager.connect(websocket, room_id, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Validate message size (max 1MB)
            if len(data) > 1024 * 1024:
                logger.warning(f"Message too large from user {user_id}: {len(data)} bytes")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Message too large"
                }, websocket)
                continue
            
            # Validate WebSocket message structure
            try:
                raw_message = json.loads(data)
                message = WebSocketMessage.parse_obj(raw_message)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Invalid WebSocket message from user {user_id}: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid message format",
                    "details": str(e)
                }, websocket)
                continue
            
            message_type = message.type
            
            if message_type == "typing":
                # Handle typing indicators with validation
                try:
                    typing_data = TypingIndicatorData.parse_obj({"is_typing": message.is_typing})
                    await connection_manager.send_typing_indicator(
                        room_id, user_id, typing_data.is_typing
                    )
                except ValidationError as e:
                    logger.error(f"Invalid typing indicator data from user {user_id}: {e}")
            
            elif message_type == "presence":
                # Handle user presence updates with validation
                try:
                    presence_data = PresenceData.parse_obj({"status": message.status or "online"})
                    await connection_manager.send_user_presence(
                        room_id, user_id, presence_data.status
                    )
                except ValidationError as e:
                    logger.error(f"Invalid presence data from user {user_id}: {e}")
            
            elif message_type == "ping":
                # Handle ping/keepalive
                await connection_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            
            elif message_type == "annotation_update":
                # Handle real-time annotation updates with validation
                try:
                    raw_data = message.data or {}
                    annotation_data = AnnotationUpdateData.parse_obj(raw_data)
                    await collaboration_manager.notify_annotation_added(
                        room_id, annotation_data.dict(), user_id
                    )
                except ValidationError as e:
                    logger.error(f"Invalid annotation_update data from user {user_id}: {e}")
                    await connection_manager.send_personal_message({
                        "type": "error",
                        "message": "Invalid annotation data format",
                        "details": str(e)
                    }, websocket)
            
            # Update last activity
            if websocket in connection_manager.connection_metadata:
                connection_manager.connection_metadata[websocket]["last_activity"] = datetime.utcnow()
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


@router.get("/conflicts/{conflict_id}/comments")
def get_conflict_comments(
    conflict_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get comments for a conflict"""
    # Verify access to conflict
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Check if user has access to the project
    project = db.query(Project).filter(
        Project.id == conflict.project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get comments with pagination
    comments_query = db.query(Comment).filter(
        Comment.conflict_id == conflict_id
    ).order_by(Comment.created_at.desc())
    
    # Filter internal comments for non-team members
    if not current_user.is_superuser:
        comments_query = comments_query.filter(Comment.is_internal == False)
    
    comments = comments_query.offset(offset).limit(limit).all()
    
    # Format response
    comment_list = []
    for comment in comments:
        user = db.query(User).filter(User.id == comment.user_id).first()
        comment_data = {
            "id": comment.id,
            "message": comment.message,
            "comment_type": comment.comment_type,
            "is_internal": comment.is_internal,
            "is_edited": comment.is_edited,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
            "edited_at": comment.edited_at,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email
            } if user else None,
            "attachments": [
                {
                    "id": att.id,
                    "filename": att.filename,
                    "file_size": att.file_size,
                    "file_type": att.file_type,
                    "created_at": att.created_at
                }
                for att in comment.attachments
            ],
            "replies": []  # TODO: Implement nested replies if needed
        }
        comment_list.append(comment_data)
    
    return {
        "comments": comment_list,
        "total": db.query(Comment).filter(Comment.conflict_id == conflict_id).count(),
        "offset": offset,
        "limit": limit
    }


@router.post("/conflicts/{conflict_id}/comments")
async def add_comment(
    conflict_id: int,
    comment_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Add a comment to a conflict"""
    # Verify access to conflict
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Check if user has access to the project
    project = db.query(Project).filter(
        Project.id == conflict.project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create comment
    comment = Comment(
        conflict_id=conflict_id,
        user_id=current_user.id,
        message=comment_data.get("message", ""),
        comment_type=comment_data.get("comment_type", "general"),
        is_internal=comment_data.get("is_internal", False),
        parent_comment_id=comment_data.get("parent_comment_id")
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Create activity log
    activity = ActivityLog(
        project_id=conflict.project_id,
        conflict_id=conflict_id,
        user_id=current_user.id,
        activity_type="comment_added",
        action="create",
        entity_type="comment",
        entity_id=comment.id,
        description=f"{current_user.full_name} added a comment to conflict {conflict_id}"
    )
    db.add(activity)
    db.commit()
    
    # Format response
    comment_response = {
        "id": comment.id,
        "message": comment.message,
        "comment_type": comment.comment_type,
        "is_internal": comment.is_internal,
        "created_at": comment.created_at,
        "user": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email
        }
    }
    
    # Notify via WebSocket
    room_id = f"conflict_{conflict_id}"
    await collaboration_manager.notify_comment_added(
        room_id, comment_response, current_user.id
    )
    
    return comment_response


@router.post("/conflicts/{conflict_id}/comments/{comment_id}/attachments")
async def upload_comment_attachment(
    conflict_id: int,
    comment_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Upload attachment to a comment"""
    # Verify comment exists and user has access
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.conflict_id == conflict_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Verify access to conflict
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    project = db.query(Project).filter(
        Project.id == conflict.project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Save file
    import uuid
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Create attachment record
    attachment = CommentAttachment(
        comment_id=comment_id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        file_type=file.content_type
    )
    
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    
    return {
        "id": attachment.id,
        "filename": attachment.filename,
        "file_size": attachment.file_size,
        "file_type": attachment.file_type,
        "created_at": attachment.created_at
    }


@router.get("/conflicts/{conflict_id}/annotations")
def get_conflict_annotations(
    conflict_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get annotations for a conflict"""
    # Verify access to conflict
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Check if user has access to the project
    project = db.query(Project).filter(
        Project.id == conflict.project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get annotations
    annotations = db.query(Annotation).filter(
        Annotation.conflict_id == conflict_id,
        Annotation.is_visible == True
    ).order_by(Annotation.created_at.desc()).all()
    
    # Format response
    annotation_list = []
    for annotation in annotations:
        user = db.query(User).filter(User.id == annotation.user_id).first()
        resolved_by = None
        if annotation.resolved_by_id:
            resolved_by = db.query(User).filter(User.id == annotation.resolved_by_id).first()
        
        annotation_data = {
            "id": annotation.id,
            "annotation_type": annotation.annotation_type,
            "title": annotation.title,
            "description": annotation.description,
            "position_data": json.loads(annotation.position_data) if annotation.position_data else None,
            "visual_data": json.loads(annotation.visual_data) if annotation.visual_data else None,
            "is_resolved": annotation.is_resolved,
            "priority": annotation.priority,
            "created_at": annotation.created_at,
            "updated_at": annotation.updated_at,
            "resolved_at": annotation.resolved_at,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email
            } if user else None,
            "resolved_by": {
                "id": resolved_by.id,
                "full_name": resolved_by.full_name
            } if resolved_by else None
        }
        annotation_list.append(annotation_data)
    
    return annotation_list


@router.post("/conflicts/{conflict_id}/annotations")
async def add_annotation(
    conflict_id: int,
    annotation_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Add an annotation to a conflict"""
    # Verify access to conflict
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Check if user has access to the project
    project = db.query(Project).filter(
        Project.id == conflict.project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create annotation
    annotation = Annotation(
        conflict_id=conflict_id,
        element_id=annotation_data.get("element_id"),
        user_id=current_user.id,
        annotation_type=annotation_data.get("annotation_type", "point"),
        title=annotation_data.get("title", ""),
        description=annotation_data.get("description", ""),
        position_data=json.dumps(annotation_data.get("position_data", {})),
        visual_data=json.dumps(annotation_data.get("visual_data", {})),
        priority=annotation_data.get("priority", "medium")
    )
    
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    
    # Create activity log
    activity = ActivityLog(
        project_id=conflict.project_id,
        conflict_id=conflict_id,
        user_id=current_user.id,
        activity_type="annotation_added",
        action="create",
        entity_type="annotation",
        entity_id=annotation.id,
        description=f"{current_user.full_name} added an annotation to conflict {conflict_id}"
    )
    db.add(activity)
    db.commit()
    
    # Format response
    annotation_response = {
        "id": annotation.id,
        "annotation_type": annotation.annotation_type,
        "title": annotation.title,
        "description": annotation.description,
        "position_data": json.loads(annotation.position_data) if annotation.position_data else None,
        "visual_data": json.loads(annotation.visual_data) if annotation.visual_data else None,
        "priority": annotation.priority,
        "created_at": annotation.created_at,
        "user": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email
        }
    }
    
    # Notify via WebSocket
    room_id = f"conflict_{conflict_id}"
    await collaboration_manager.notify_annotation_added(
        room_id, annotation_response, current_user.id
    )
    
    return annotation_response


@router.get("/conflicts/{conflict_id}/activity")
def get_conflict_activity(
    conflict_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get activity log for a conflict"""
    # Verify access to conflict
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Check if user has access to the project
    project = db.query(Project).filter(
        Project.id == conflict.project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get activity logs
    activities = db.query(ActivityLog).filter(
        ActivityLog.conflict_id == conflict_id
    ).order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit).all()
    
    # Format response
    activity_list = []
    for activity in activities:
        user = db.query(User).filter(User.id == activity.user_id).first()
        activity_data = {
            "id": activity.id,
            "activity_type": activity.activity_type,
            "action": activity.action,
            "entity_type": activity.entity_type,
            "entity_id": activity.entity_id,
            "description": activity.description,
            "old_values": json.loads(activity.old_values) if activity.old_values else None,
            "new_values": json.loads(activity.new_values) if activity.new_values else None,
            "metadata": json.loads(activity.metadata) if activity.metadata else None,
            "created_at": activity.created_at,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email
            } if user else None
        }
        activity_list.append(activity_data)
    
    return {
        "activities": activity_list,
        "total": db.query(ActivityLog).filter(ActivityLog.conflict_id == conflict_id).count(),
        "offset": offset,
        "limit": limit
    }


@router.get("/projects/{project_id}/activity")
def get_project_activity(
    project_id: int,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get activity log for a project"""
    # Check if user has access to the project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get activity logs
    activities = db.query(ActivityLog).filter(
        ActivityLog.project_id == project_id
    ).order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit).all()
    
    # Format response
    activity_list = []
    for activity in activities:
        user = db.query(User).filter(User.id == activity.user_id).first()
        activity_data = {
            "id": activity.id,
            "conflict_id": activity.conflict_id,
            "activity_type": activity.activity_type,
            "action": activity.action,
            "entity_type": activity.entity_type,
            "entity_id": activity.entity_id,
            "description": activity.description,
            "created_at": activity.created_at,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email
            } if user else None
        }
        activity_list.append(activity_data)
    
    return {
        "activities": activity_list,
        "total": db.query(ActivityLog).filter(ActivityLog.project_id == project_id).count(),
        "offset": offset,
        "limit": limit
    }


@router.get("/ws/stats")
def get_websocket_stats(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get WebSocket connection statistics (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return connection_manager.get_global_stats()


@router.get("/conflicts/{conflict_id}/presence")
def get_room_presence(
    conflict_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get current users in conflict room"""
    # Verify access to conflict
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Check if user has access to the project
    project = db.query(Project).filter(
        Project.id == conflict.project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    room_id = f"conflict_{conflict_id}"
    stats = connection_manager.get_room_stats(room_id)
    
    # Get user details for active users
    active_users = []
    for user_id in stats["active_users"]:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            active_users.append({
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email
            })
    
    return {
        "conflict_id": conflict_id,
        "active_connections": stats["active_connections"],
        "active_users": active_users
    }