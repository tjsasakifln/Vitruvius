# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class ProjectRole(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


class PermissionType(enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"


class Permission(Base):
    """
    Defines specific permissions that can be granted to roles
    """
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500))
    permission_type = Column(Enum(PermissionType), nullable=False)
    resource_type = Column(String(50), nullable=False)  # 'project', 'conflict', 'solution', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission")


class Role(Base):
    """
    Defines roles with associated permissions
    """
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(500))
    is_system_role = Column(Boolean, default=False)  # System roles cannot be deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="role")
    user_roles = relationship("UserRole", back_populates="role")


class RolePermission(Base):
    """
    Many-to-many relationship between roles and permissions
    """
    __tablename__ = "role_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate role-permission assignments
    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),)
    
    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class UserRole(Base):
    """
    Assigns roles to users within specific projects
    """
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    is_active = Column(Boolean, default=True)
    
    # Unique constraint to prevent duplicate user-role assignments per project
    __table_args__ = (UniqueConstraint('user_id', 'role_id', 'project_id', name='uq_user_role_project'),)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    project = relationship("Project")
    granter = relationship("User", foreign_keys=[granted_by])


class ProjectInvitation(Base):
    """
    Manages project invitations for users
    """
    __tablename__ = "project_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    invited_email = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    invitation_token = Column(String(255), unique=True, nullable=False)
    invited_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    project = relationship("Project")
    role = relationship("Role")
    inviter = relationship("User")


class AuditLog(Base):
    """
    Tracks permission changes and security events
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    action = Column(String(100), nullable=False)  # 'grant_role', 'revoke_role', 'login', etc.
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=True)
    old_value = Column(String(1000), nullable=True)
    new_value = Column(String(1000), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    project = relationship("Project")


def create_default_roles_and_permissions():
    """
    Create default roles and permissions for the system
    """
    # Default permissions
    permissions = [
        # Project permissions
        Permission(name="view_project", description="View project details", permission_type=PermissionType.READ, resource_type="project"),
        Permission(name="edit_project", description="Edit project settings", permission_type=PermissionType.WRITE, resource_type="project"),
        Permission(name="delete_project", description="Delete project", permission_type=PermissionType.DELETE, resource_type="project"),
        Permission(name="manage_project_users", description="Manage project users", permission_type=PermissionType.MANAGE_USERS, resource_type="project"),
        
        # Conflict permissions
        Permission(name="view_conflicts", description="View conflicts", permission_type=PermissionType.READ, resource_type="conflict"),
        Permission(name="edit_conflicts", description="Edit conflict details", permission_type=PermissionType.WRITE, resource_type="conflict"),
        Permission(name="delete_conflicts", description="Delete conflicts", permission_type=PermissionType.DELETE, resource_type="conflict"),
        
        # Solution permissions
        Permission(name="view_solutions", description="View solutions", permission_type=PermissionType.READ, resource_type="solution"),
        Permission(name="edit_solutions", description="Edit solutions", permission_type=PermissionType.WRITE, resource_type="solution"),
        Permission(name="delete_solutions", description="Delete solutions", permission_type=PermissionType.DELETE, resource_type="solution"),
        
        # File permissions
        Permission(name="upload_files", description="Upload IFC files", permission_type=PermissionType.WRITE, resource_type="file"),
        Permission(name="delete_files", description="Delete files", permission_type=PermissionType.DELETE, resource_type="file"),
        
        # Comment permissions
        Permission(name="view_comments", description="View comments", permission_type=PermissionType.READ, resource_type="comment"),
        Permission(name="add_comments", description="Add comments", permission_type=PermissionType.WRITE, resource_type="comment"),
        Permission(name="edit_comments", description="Edit comments", permission_type=PermissionType.WRITE, resource_type="comment"),
        Permission(name="delete_comments", description="Delete comments", permission_type=PermissionType.DELETE, resource_type="comment"),
    ]
    
    # Default roles
    roles = [
        Role(name="owner", description="Project owner with full permissions", is_system_role=True),
        Role(name="admin", description="Project administrator with most permissions", is_system_role=True),
        Role(name="collaborator", description="Project collaborator with edit permissions", is_system_role=True),
        Role(name="viewer", description="Project viewer with read-only permissions", is_system_role=True),
    ]
    
    return permissions, roles


def get_default_role_permissions():
    """
    Define default permissions for each role
    """
    return {
        "owner": [
            "view_project", "edit_project", "delete_project", "manage_project_users",
            "view_conflicts", "edit_conflicts", "delete_conflicts",
            "view_solutions", "edit_solutions", "delete_solutions",
            "upload_files", "delete_files",
            "view_comments", "add_comments", "edit_comments", "delete_comments"
        ],
        "admin": [
            "view_project", "edit_project", "manage_project_users",
            "view_conflicts", "edit_conflicts", "delete_conflicts",
            "view_solutions", "edit_solutions", "delete_solutions",
            "upload_files", "delete_files",
            "view_comments", "add_comments", "edit_comments", "delete_comments"
        ],
        "collaborator": [
            "view_project",
            "view_conflicts", "edit_conflicts",
            "view_solutions", "edit_solutions",
            "upload_files",
            "view_comments", "add_comments", "edit_comments"
        ],
        "viewer": [
            "view_project",
            "view_conflicts",
            "view_solutions",
            "view_comments"
        ]
    }