# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parent_comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True, index=True)  # For replies
    message = Column(Text, nullable=False)
    comment_type = Column(String(50), default="general", index=True)  # 'general', 'solution_review', 'annotation', 'status_update'
    is_internal = Column(Boolean, default=False, index=True)  # Internal comments for team only
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conflict = relationship("Conflict", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent_comment = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship("Comment", back_populates="parent_comment")
    attachments = relationship("CommentAttachment", back_populates="comment")


class CommentAttachment(Base):
    __tablename__ = "comment_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    file_type = Column(String(100))  # MIME type
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    comment = relationship("Comment", back_populates="attachments")


class Annotation(Base):
    __tablename__ = "annotations"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False, index=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=True, index=True)  # Optional element reference
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    annotation_type = Column(String(50), nullable=False, index=True)  # 'highlight', 'point', 'area', 'measurement'
    title = Column(String(255))
    description = Column(Text)
    
    # 3D/2D positioning data (stored as JSON strings)
    position_data = Column(Text)  # JSON: coordinates, camera position, etc.
    visual_data = Column(Text)   # JSON: colors, styles, measurements
    
    # Status and visibility
    is_resolved = Column(Boolean, default=False, index=True)
    is_visible = Column(Boolean, default=True)
    priority = Column(String(20), default="medium", index=True)  # 'low', 'medium', 'high', 'critical'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Relationships
    conflict = relationship("Conflict", back_populates="annotations")
    element = relationship("Element", back_populates="annotations")
    user = relationship("User", foreign_keys=[user_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=True, index=True)  # Optional conflict reference
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Activity details
    activity_type = Column(String(100), nullable=False, index=True)  # 'conflict_created', 'solution_added', 'comment_posted', etc.
    action = Column(String(50), nullable=False)  # 'create', 'update', 'delete', 'resolve', 'assign'
    entity_type = Column(String(50), nullable=False, index=True)  # 'conflict', 'solution', 'comment', 'annotation'
    entity_id = Column(Integer, nullable=True)  # ID of the affected entity
    
    # Change tracking
    old_values = Column(Text, nullable=True)  # JSON string of old values
    new_values = Column(Text, nullable=True)  # JSON string of new values
    
    # Context and metadata
    description = Column(Text)  # Human-readable description
    metadata = Column(Text)  # Additional context as JSON
    ip_address = Column(String(45))  # IPv4/IPv6 address
    user_agent = Column(String(500))  # Browser/client information
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="activity_logs")
    conflict = relationship("Conflict", back_populates="activity_logs")
    user = relationship("User", back_populates="activity_logs")


class ConflictAssignment(Base):
    __tablename__ = "conflict_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), default="resolver")  # 'resolver', 'reviewer', 'observer'
    
    # Assignment details
    due_date = Column(DateTime, nullable=True)
    priority = Column(String(20), default="medium")
    notes = Column(Text)
    
    # Status tracking
    status = Column(String(50), default="assigned", index=True)  # 'assigned', 'accepted', 'working', 'completed', 'declined'
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conflict = relationship("Conflict", back_populates="assignments")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])


class WorkflowState(Base):
    __tablename__ = "workflow_states"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)  # 'open', 'investigating', 'solution_proposed', 'under_review', 'resolved', 'closed'
    previous_state = Column(String(50), nullable=True)
    
    # State change details
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(Text)  # Reason for state change
    automatic = Column(Boolean, default=False)  # Whether change was automatic
    
    # Workflow metadata
    workflow_data = Column(Text)  # JSON data for workflow-specific information
    approval_required = Column(Boolean, default=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conflict = relationship("Conflict", back_populates="workflow_states")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=True, index=True)
    
    # Notification details
    notification_type = Column(String(100), nullable=False, index=True)  # 'comment_reply', 'conflict_assigned', 'solution_added', etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Status and metadata
    is_read = Column(Boolean, default=False, index=True)
    is_email_sent = Column(Boolean, default=False)
    priority = Column(String(20), default="normal", index=True)  # 'low', 'normal', 'high', 'urgent'
    
    # Related entity information
    related_entity_type = Column(String(50))  # 'comment', 'solution', 'annotation'
    related_entity_id = Column(Integer)
    
    # Action information (for actionable notifications)
    action_url = Column(String(500))  # URL to take action
    action_text = Column(String(100))  # Text for action button
    
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    project = relationship("Project")
    conflict = relationship("Conflict")


class ConflictWatch(Base):
    __tablename__ = "conflict_watches"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Watch preferences
    watch_comments = Column(Boolean, default=True)
    watch_solutions = Column(Boolean, default=True)
    watch_status_changes = Column(Boolean, default=True)
    watch_annotations = Column(Boolean, default=False)
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True)
    in_app_notifications = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conflict = relationship("Conflict", back_populates="watchers")
    user = relationship("User")


# Update existing models to include relationships
# Note: These would need to be added to the existing models in project.py

# Add to User model:
# comments = relationship("Comment", back_populates="user")
# activity_logs = relationship("ActivityLog", back_populates="user")
# notifications = relationship("Notification", back_populates="user")

# Add to Conflict model:
# comments = relationship("Comment", back_populates="conflict")
# annotations = relationship("Annotation", back_populates="conflict")
# activity_logs = relationship("ActivityLog", back_populates="conflict")
# assignments = relationship("ConflictAssignment", back_populates="conflict")
# workflow_states = relationship("WorkflowState", back_populates="conflict")
# watchers = relationship("ConflictWatch", back_populates="conflict")

# Add to Element model:
# annotations = relationship("Annotation", back_populates="element")

# Add to Project model:
# activity_logs = relationship("ActivityLog", back_populates="project")