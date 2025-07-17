# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime

from ..db.models.collaboration import ActivityLog, Notification
from ..db.models.project import User, Project, Conflict


class ActivityLogger:
    """Service for logging user activities and creating audit trails"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_activity(
        self,
        project_id: int,
        user_id: int,
        activity_type: str,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        conflict_id: Optional[int] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ActivityLog:
        """
        Log an activity with comprehensive details
        
        Args:
            project_id: ID of the project
            user_id: ID of the user performing the action
            activity_type: Type of activity (e.g., 'conflict_created', 'comment_added')
            action: Action performed ('create', 'update', 'delete', 'resolve', 'assign')
            entity_type: Type of entity affected ('conflict', 'solution', 'comment', 'annotation')
            entity_id: ID of the affected entity
            conflict_id: Optional conflict ID if activity is conflict-related
            description: Human-readable description
            old_values: Previous values (for updates)
            new_values: New values (for updates/creates)
            metadata: Additional context information
            ip_address: User's IP address
            user_agent: User's browser/client information
        """
        activity = ActivityLog(
            project_id=project_id,
            conflict_id=conflict_id,
            user_id=user_id,
            activity_type=activity_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            description=description,
            metadata=json.dumps(metadata) if metadata else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        
        return activity
    
    def log_conflict_created(
        self,
        project_id: int,
        user_id: int,
        conflict_id: int,
        conflict_data: Dict[str, Any],
        **kwargs
    ) -> ActivityLog:
        """Log conflict creation"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            conflict_id=conflict_id,
            activity_type="conflict_created",
            action="create",
            entity_type="conflict",
            entity_id=conflict_id,
            description=f"Created conflict: {conflict_data.get('conflict_type', 'Unknown')}",
            new_values=conflict_data,
            **kwargs
        )
    
    def log_conflict_updated(
        self,
        project_id: int,
        user_id: int,
        conflict_id: int,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        **kwargs
    ) -> ActivityLog:
        """Log conflict update"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            conflict_id=conflict_id,
            activity_type="conflict_updated",
            action="update",
            entity_type="conflict",
            entity_id=conflict_id,
            description="Updated conflict details",
            old_values=old_values,
            new_values=new_values,
            **kwargs
        )
    
    def log_conflict_status_changed(
        self,
        project_id: int,
        user_id: int,
        conflict_id: int,
        old_status: str,
        new_status: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> ActivityLog:
        """Log conflict status change"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            conflict_id=conflict_id,
            activity_type="conflict_status_changed",
            action="update",
            entity_type="conflict",
            entity_id=conflict_id,
            description=f"Changed conflict status from {old_status} to {new_status}",
            old_values={"status": old_status},
            new_values={"status": new_status, "reason": reason},
            **kwargs
        )
    
    def log_solution_added(
        self,
        project_id: int,
        user_id: int,
        conflict_id: int,
        solution_id: int,
        solution_data: Dict[str, Any],
        **kwargs
    ) -> ActivityLog:
        """Log solution addition"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            conflict_id=conflict_id,
            activity_type="solution_added",
            action="create",
            entity_type="solution",
            entity_id=solution_id,
            description=f"Added solution: {solution_data.get('solution_type', 'Unknown')}",
            new_values=solution_data,
            **kwargs
        )
    
    def log_comment_added(
        self,
        project_id: int,
        user_id: int,
        conflict_id: int,
        comment_id: int,
        comment_type: str = "general",
        **kwargs
    ) -> ActivityLog:
        """Log comment addition"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            conflict_id=conflict_id,
            activity_type="comment_added",
            action="create",
            entity_type="comment",
            entity_id=comment_id,
            description=f"Added {comment_type} comment",
            new_values={"comment_type": comment_type},
            **kwargs
        )
    
    def log_annotation_added(
        self,
        project_id: int,
        user_id: int,
        conflict_id: int,
        annotation_id: int,
        annotation_type: str,
        **kwargs
    ) -> ActivityLog:
        """Log annotation addition"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            conflict_id=conflict_id,
            activity_type="annotation_added",
            action="create",
            entity_type="annotation",
            entity_id=annotation_id,
            description=f"Added {annotation_type} annotation",
            new_values={"annotation_type": annotation_type},
            **kwargs
        )
    
    def log_feedback_submitted(
        self,
        project_id: int,
        user_id: int,
        conflict_id: int,
        feedback_id: int,
        feedback_type: str,
        effectiveness_rating: Optional[int] = None,
        **kwargs
    ) -> ActivityLog:
        """Log solution feedback submission"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            conflict_id=conflict_id,
            activity_type="feedback_submitted",
            action="create",
            entity_type="feedback",
            entity_id=feedback_id,
            description=f"Submitted {feedback_type} feedback",
            new_values={
                "feedback_type": feedback_type,
                "effectiveness_rating": effectiveness_rating
            },
            **kwargs
        )
    
    def log_user_assignment(
        self,
        project_id: int,
        assigner_user_id: int,
        assigned_user_id: int,
        conflict_id: int,
        role: str,
        **kwargs
    ) -> ActivityLog:
        """Log user assignment to conflict"""
        return self.log_activity(
            project_id=project_id,
            user_id=assigner_user_id,
            conflict_id=conflict_id,
            activity_type="user_assigned",
            action="assign",
            entity_type="conflict",
            entity_id=conflict_id,
            description=f"Assigned user {assigned_user_id} as {role}",
            new_values={
                "assigned_user_id": assigned_user_id,
                "role": role
            },
            **kwargs
        )
    
    def log_file_upload(
        self,
        project_id: int,
        user_id: int,
        file_type: str,
        filename: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        conflict_id: Optional[int] = None,
        **kwargs
    ) -> ActivityLog:
        """Log file upload"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            conflict_id=conflict_id,
            activity_type="file_uploaded",
            action="create",
            entity_type=entity_type or "file",
            entity_id=entity_id,
            description=f"Uploaded {file_type}: {filename}",
            new_values={
                "filename": filename,
                "file_type": file_type
            },
            **kwargs
        )
    
    def log_integration_sync(
        self,
        project_id: int,
        user_id: int,
        integration_type: str,
        sync_status: str,
        entity_count: int = 0,
        error_message: Optional[str] = None,
        **kwargs
    ) -> ActivityLog:
        """Log integration synchronization"""
        return self.log_activity(
            project_id=project_id,
            user_id=user_id,
            activity_type="integration_sync",
            action="sync",
            entity_type="integration",
            description=f"Synchronized with {integration_type}: {sync_status}",
            new_values={
                "integration_type": integration_type,
                "sync_status": sync_status,
                "entity_count": entity_count,
                "error_message": error_message
            },
            **kwargs
        )
    
    def get_project_timeline(
        self,
        project_id: int,
        limit: int = 100,
        offset: int = 0,
        activity_types: Optional[List[str]] = None,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ActivityLog]:
        """
        Get project activity timeline with filtering options
        """
        query = self.db.query(ActivityLog).filter(ActivityLog.project_id == project_id)
        
        if activity_types:
            query = query.filter(ActivityLog.activity_type.in_(activity_types))
        
        if user_ids:
            query = query.filter(ActivityLog.user_id.in_(user_ids))
        
        if start_date:
            query = query.filter(ActivityLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(ActivityLog.created_at <= end_date)
        
        return query.order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_conflict_timeline(
        self,
        conflict_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get activity timeline for a specific conflict"""
        return self.db.query(ActivityLog).filter(
            ActivityLog.conflict_id == conflict_id
        ).order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_user_activity_summary(
        self,
        user_id: int,
        project_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get activity summary for a user"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        query = self.db.query(ActivityLog).filter(
            ActivityLog.user_id == user_id,
            ActivityLog.created_at >= start_date
        )
        
        if project_id:
            query = query.filter(ActivityLog.project_id == project_id)
        
        activities = query.all()
        
        # Count activities by type
        activity_counts = {}
        for activity in activities:
            activity_type = activity.activity_type
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
        
        # Count activities by day
        daily_counts = {}
        for activity in activities:
            day = activity.created_at.date()
            daily_counts[day.isoformat()] = daily_counts.get(day.isoformat(), 0) + 1
        
        return {
            "total_activities": len(activities),
            "activity_counts": activity_counts,
            "daily_counts": daily_counts,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }


class NotificationService:
    """Service for managing user notifications"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        project_id: Optional[int] = None,
        conflict_id: Optional[int] = None,
        priority: str = "normal",
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None
    ) -> Notification:
        """Create a new notification"""
        notification = Notification(
            user_id=user_id,
            project_id=project_id,
            conflict_id=conflict_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            action_url=action_url,
            action_text=action_text
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        return notification
    
    def notify_comment_reply(
        self,
        replier_user_id: int,
        parent_comment_user_id: int,
        conflict_id: int,
        project_id: int
    ):
        """Notify user about comment reply"""
        if replier_user_id == parent_comment_user_id:
            return  # Don't notify self
        
        conflict = self.db.query(Conflict).filter(Conflict.id == conflict_id).first()
        replier = self.db.query(User).filter(User.id == replier_user_id).first()
        
        if conflict and replier:
            self.create_notification(
                user_id=parent_comment_user_id,
                notification_type="comment_reply",
                title="New Reply to Your Comment",
                message=f"{replier.full_name} replied to your comment on conflict: {conflict.conflict_type}",
                project_id=project_id,
                conflict_id=conflict_id,
                related_entity_type="comment",
                action_url=f"/projects/{project_id}/conflicts/{conflict_id}",
                action_text="View Comment"
            )
    
    def notify_conflict_assignment(
        self,
        assigned_user_id: int,
        assigner_user_id: int,
        conflict_id: int,
        project_id: int,
        role: str
    ):
        """Notify user about conflict assignment"""
        conflict = self.db.query(Conflict).filter(Conflict.id == conflict_id).first()
        assigner = self.db.query(User).filter(User.id == assigner_user_id).first()
        
        if conflict and assigner:
            self.create_notification(
                user_id=assigned_user_id,
                notification_type="conflict_assigned",
                title="New Conflict Assignment",
                message=f"{assigner.full_name} assigned you as {role} for conflict: {conflict.conflict_type}",
                project_id=project_id,
                conflict_id=conflict_id,
                priority="high",
                related_entity_type="conflict",
                action_url=f"/projects/{project_id}/conflicts/{conflict_id}",
                action_text="View Conflict"
            )
    
    def notify_solution_added(
        self,
        conflict_watchers: List[int],
        solution_creator_id: int,
        conflict_id: int,
        project_id: int
    ):
        """Notify watchers about new solution"""
        conflict = self.db.query(Conflict).filter(Conflict.id == conflict_id).first()
        creator = self.db.query(User).filter(User.id == solution_creator_id).first()
        
        if conflict and creator:
            for user_id in conflict_watchers:
                if user_id != solution_creator_id:  # Don't notify creator
                    self.create_notification(
                        user_id=user_id,
                        notification_type="solution_added",
                        title="New Solution Proposed",
                        message=f"{creator.full_name} proposed a solution for conflict: {conflict.conflict_type}",
                        project_id=project_id,
                        conflict_id=conflict_id,
                        related_entity_type="solution",
                        action_url=f"/projects/{project_id}/conflicts/{conflict_id}",
                        action_text="Review Solution"
                    )
    
    def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
    
    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get notifications for a user"""
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user"""
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()