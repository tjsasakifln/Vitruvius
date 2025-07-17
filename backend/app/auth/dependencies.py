# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional

from ..db.database import get_db
from ..db.models.project import User
from ..services.rbac_service import get_rbac_service, AccessDecision
from .auth import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_permission(permission: str):
    """
    Decorator to require specific permission for project access
    
    Args:
        permission: Permission name required
        
    Returns:
        Dependency function
    """
    def permission_checker(
        project_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
        request: Request = None
    ):
        rbac_service = get_rbac_service(db)
        
        # Initialize RBAC system if not already done
        rbac_service.initialize_rbac_system()
        
        # Check permission
        access_decision = rbac_service.check_permission(current_user.id, project_id, permission)
        
        if access_decision != AccessDecision.ALLOW:
            # Audit log the denied access
            ip_address = getattr(request.client, 'host', None) if request else None
            user_agent = request.headers.get("user-agent") if request else None
            
            rbac_service.audit_log(
                user_id=current_user.id,
                project_id=project_id,
                action="access_denied",
                resource_type="project",
                resource_id=project_id,
                old_value=f"Permission: {permission}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        
        return current_user
    
    return permission_checker

def require_project_access(permission: str = "view_project"):
    """
    Simplified project access dependency
    
    Args:
        permission: Permission required (default: view_project)
        
    Returns:
        Dependency function
    """
    return require_permission(permission)

class ProjectAccessChecker:
    """
    Class-based permission checker for more complex scenarios
    """
    
    def __init__(self, required_permissions: list):
        self.required_permissions = required_permissions
    
    def __call__(
        self,
        project_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
        request: Request = None
    ):
        rbac_service = get_rbac_service(db)
        
        # Initialize RBAC system if not already done
        rbac_service.initialize_rbac_system()
        
        # Check all required permissions
        for permission in self.required_permissions:
            access_decision = rbac_service.check_permission(current_user.id, project_id, permission)
            
            if access_decision != AccessDecision.ALLOW:
                # Audit log the denied access
                ip_address = getattr(request.client, 'host', None) if request else None
                user_agent = request.headers.get("user-agent") if request else None
                
                rbac_service.audit_log(
                    user_id=current_user.id,
                    project_id=project_id,
                    action="access_denied",
                    resource_type="project",
                    resource_id=project_id,
                    old_value=f"Permission: {permission}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission}"
                )
        
        return current_user

# Common permission dependencies
require_project_view = require_permission("view_project")
require_project_edit = require_permission("edit_project")
require_project_delete = require_permission("delete_project")
require_project_user_management = require_permission("manage_project_users")
require_file_upload = require_permission("upload_files")
require_conflict_edit = require_permission("edit_conflicts")
require_solution_edit = require_permission("edit_solutions")
require_comment_add = require_permission("add_comments")