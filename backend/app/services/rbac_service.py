# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
import secrets
import hashlib
from enum import Enum

from ..db.models.rbac import (
    Permission, Role, RolePermission, UserRole, ProjectInvitation, AuditLog,
    PermissionType, ProjectRole, create_default_roles_and_permissions, get_default_role_permissions
)
from ..db.models.project import User, Project


class AccessDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"


class RBACService:
    """
    Role-Based Access Control service for managing permissions
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def initialize_rbac_system(self):
        """
        Initialize the RBAC system with default roles and permissions
        """
        # Check if already initialized
        if self.db.query(Role).count() > 0:
            return
        
        # Create default permissions and roles
        permissions, roles = create_default_roles_and_permissions()
        
        # Add permissions to database
        for permission in permissions:
            self.db.add(permission)
        
        # Add roles to database
        for role in roles:
            self.db.add(role)
        
        self.db.commit()
        
        # Assign permissions to roles
        role_permissions = get_default_role_permissions()
        
        for role_name, permission_names in role_permissions.items():
            role = self.db.query(Role).filter(Role.name == role_name).first()
            if role:
                for permission_name in permission_names:
                    permission = self.db.query(Permission).filter(Permission.name == permission_name).first()
                    if permission:
                        role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
                        self.db.add(role_permission)
        
        self.db.commit()
    
    def check_permission(self, user_id: int, project_id: int, permission_name: str) -> AccessDecision:
        """
        Check if a user has a specific permission for a project
        
        Args:
            user_id: ID of the user
            project_id: ID of the project
            permission_name: Name of the permission to check
            
        Returns:
            AccessDecision: ALLOW or DENY
        """
        try:
            # Get user roles for the project
            user_roles = self.db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.project_id == project_id,
                    UserRole.is_active == True,
                    or_(UserRole.expires_at.is_(None), UserRole.expires_at > datetime.utcnow())
                )
            ).all()
            
            if not user_roles:
                # Check if user is project owner (fallback)
                project = self.db.query(Project).filter(Project.id == project_id).first()
                if project and project.owner_id == user_id:
                    return AccessDecision.ALLOW
                return AccessDecision.DENY
            
            # Check if any role has the required permission
            for user_role in user_roles:
                role_permissions = self.db.query(RolePermission).join(Permission).filter(
                    and_(
                        RolePermission.role_id == user_role.role_id,
                        Permission.name == permission_name
                    )
                ).first()
                
                if role_permissions:
                    return AccessDecision.ALLOW
            
            return AccessDecision.DENY
            
        except Exception as e:
            # Log error and deny access for security
            self.audit_log(
                user_id=user_id,
                project_id=project_id,
                action="permission_check_error",
                resource_type="permission",
                old_value=permission_name,
                new_value=f"Error: {str(e)}"
            )
            return AccessDecision.DENY
    
    def assign_role_to_user(self, user_id: int, project_id: int, role_name: str, granted_by: int) -> bool:
        """
        Assign a role to a user for a specific project
        
        Args:
            user_id: ID of the user
            project_id: ID of the project
            role_name: Name of the role to assign
            granted_by: ID of the user granting the role
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if granter has permission to manage users
            if not self.check_permission(granted_by, project_id, "manage_project_users") == AccessDecision.ALLOW:
                return False
            
            # Get the role
            role = self.db.query(Role).filter(Role.name == role_name).first()
            if not role:
                return False
            
            # Check if user already has this role
            existing_role = self.db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.project_id == project_id,
                    UserRole.role_id == role.id,
                    UserRole.is_active == True
                )
            ).first()
            
            if existing_role:
                return True  # Already has the role
            
            # Create new role assignment
            user_role = UserRole(
                user_id=user_id,
                role_id=role.id,
                project_id=project_id,
                granted_by=granted_by
            )
            
            self.db.add(user_role)
            self.db.commit()
            
            # Audit log
            self.audit_log(
                user_id=granted_by,
                project_id=project_id,
                action="grant_role",
                resource_type="user_role",
                resource_id=user_role.id,
                new_value=f"Granted {role_name} to user {user_id}"
            )
            
            return True
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def revoke_role_from_user(self, user_id: int, project_id: int, role_name: str, revoked_by: int) -> bool:
        """
        Revoke a role from a user for a specific project
        
        Args:
            user_id: ID of the user
            project_id: ID of the project
            role_name: Name of the role to revoke
            revoked_by: ID of the user revoking the role
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if revoker has permission to manage users
            if not self.check_permission(revoked_by, project_id, "manage_project_users") == AccessDecision.ALLOW:
                return False
            
            # Get the role
            role = self.db.query(Role).filter(Role.name == role_name).first()
            if not role:
                return False
            
            # Find and deactivate the user role
            user_role = self.db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.project_id == project_id,
                    UserRole.role_id == role.id,
                    UserRole.is_active == True
                )
            ).first()
            
            if user_role:
                user_role.is_active = False
                self.db.commit()
                
                # Audit log
                self.audit_log(
                    user_id=revoked_by,
                    project_id=project_id,
                    action="revoke_role",
                    resource_type="user_role",
                    resource_id=user_role.id,
                    old_value=f"Revoked {role_name} from user {user_id}"
                )
                
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def get_user_roles(self, user_id: int, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all roles for a user in a specific project
        
        Args:
            user_id: ID of the user
            project_id: ID of the project
            
        Returns:
            List of role dictionaries
        """
        try:
            user_roles = self.db.query(UserRole).join(Role).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.project_id == project_id,
                    UserRole.is_active == True,
                    or_(UserRole.expires_at.is_(None), UserRole.expires_at > datetime.utcnow())
                )
            ).all()
            
            return [
                {
                    "role_id": ur.role_id,
                    "role_name": ur.role.name,
                    "role_description": ur.role.description,
                    "granted_at": ur.granted_at,
                    "expires_at": ur.expires_at
                }
                for ur in user_roles
            ]
            
        except Exception as e:
            return []
    
    def get_user_permissions(self, user_id: int, project_id: int) -> List[str]:
        """
        Get all permissions for a user in a specific project
        
        Args:
            user_id: ID of the user
            project_id: ID of the project
            
        Returns:
            List of permission names
        """
        try:
            permissions = self.db.query(Permission).join(RolePermission).join(Role).join(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.project_id == project_id,
                    UserRole.is_active == True,
                    or_(UserRole.expires_at.is_(None), UserRole.expires_at > datetime.utcnow())
                )
            ).distinct().all()
            
            return [p.name for p in permissions]
            
        except Exception as e:
            return []
    
    def create_project_invitation(self, project_id: int, email: str, role_name: str, invited_by: int) -> Optional[str]:
        """
        Create an invitation for a user to join a project
        
        Args:
            project_id: ID of the project
            email: Email of the user to invite
            role_name: Name of the role to assign
            invited_by: ID of the user sending the invitation
            
        Returns:
            Invitation token if successful, None otherwise
        """
        try:
            # Check if inviter has permission to manage users
            if not self.check_permission(invited_by, project_id, "manage_project_users") == AccessDecision.ALLOW:
                return None
            
            # Get the role
            role = self.db.query(Role).filter(Role.name == role_name).first()
            if not role:
                return None
            
            # Generate invitation token
            invitation_token = secrets.token_urlsafe(32)
            
            # Create invitation
            invitation = ProjectInvitation(
                project_id=project_id,
                invited_email=email,
                role_id=role.id,
                invited_by=invited_by,
                invitation_token=invitation_token,
                expires_at=datetime.utcnow() + timedelta(days=7)  # 7 days expiry
            )
            
            self.db.add(invitation)
            self.db.commit()
            
            # Audit log
            self.audit_log(
                user_id=invited_by,
                project_id=project_id,
                action="create_invitation",
                resource_type="invitation",
                resource_id=invitation.id,
                new_value=f"Invited {email} with role {role_name}"
            )
            
            return invitation_token
            
        except Exception as e:
            self.db.rollback()
            return None
    
    def accept_invitation(self, invitation_token: str, user_id: int) -> bool:
        """
        Accept a project invitation
        
        Args:
            invitation_token: The invitation token
            user_id: ID of the user accepting the invitation
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Find the invitation
            invitation = self.db.query(ProjectInvitation).filter(
                and_(
                    ProjectInvitation.invitation_token == invitation_token,
                    ProjectInvitation.is_active == True,
                    ProjectInvitation.expires_at > datetime.utcnow()
                )
            ).first()
            
            if not invitation:
                return False
            
            # Check if user email matches
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or user.email != invitation.invited_email:
                return False
            
            # Assign role to user
            if self.assign_role_to_user(user_id, invitation.project_id, invitation.role.name, invitation.invited_by):
                # Mark invitation as accepted
                invitation.accepted_at = datetime.utcnow()
                invitation.is_active = False
                self.db.commit()
                
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def audit_log(self, user_id: Optional[int], project_id: Optional[int], action: str, 
                  resource_type: str, resource_id: Optional[int] = None, 
                  old_value: Optional[str] = None, new_value: Optional[str] = None,
                  ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """
        Log security and permission events
        
        Args:
            user_id: ID of the user performing the action
            project_id: ID of the project (if applicable)
            action: Action being performed
            resource_type: Type of resource being accessed
            resource_id: ID of the resource (if applicable)
            old_value: Previous value (for updates)
            new_value: New value (for updates)
            ip_address: IP address of the user
            user_agent: User agent string
        """
        try:
            audit_entry = AuditLog(
                user_id=user_id,
                project_id=project_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_value=old_value,
                new_value=new_value,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(audit_entry)
            self.db.commit()
            
        except Exception as e:
            # Don't let audit logging failures affect the main operation
            self.db.rollback()
    
    def get_project_users(self, project_id: int, requesting_user_id: int) -> List[Dict[str, Any]]:
        """
        Get all users with access to a project
        
        Args:
            project_id: ID of the project
            requesting_user_id: ID of the user requesting the information
            
        Returns:
            List of user dictionaries with roles
        """
        try:
            # Check if requester has permission to view project users
            if not self.check_permission(requesting_user_id, project_id, "view_project") == AccessDecision.ALLOW:
                return []
            
            # Get all users with roles in the project
            user_roles = self.db.query(UserRole).join(User).join(Role).filter(
                and_(
                    UserRole.project_id == project_id,
                    UserRole.is_active == True,
                    or_(UserRole.expires_at.is_(None), UserRole.expires_at > datetime.utcnow())
                )
            ).all()
            
            # Group by user
            users_dict = {}
            for ur in user_roles:
                if ur.user_id not in users_dict:
                    users_dict[ur.user_id] = {
                        "user_id": ur.user_id,
                        "email": ur.user.email,
                        "full_name": ur.user.full_name,
                        "roles": []
                    }
                
                users_dict[ur.user_id]["roles"].append({
                    "role_name": ur.role.name,
                    "role_description": ur.role.description,
                    "granted_at": ur.granted_at,
                    "expires_at": ur.expires_at
                })
            
            return list(users_dict.values())
            
        except Exception as e:
            return []


def get_rbac_service(db: Session) -> RBACService:
    """
    Factory function to create RBACService instance
    
    Args:
        db: Database session
        
    Returns:
        RBACService instance
    """
    return RBACService(db)