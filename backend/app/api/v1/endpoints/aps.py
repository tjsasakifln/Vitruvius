# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import tempfile
import logging
from datetime import datetime

from ....db.database import get_db
from ....db.models.project import User, Project, IFCModel, Conflict
from ....auth.dependencies import get_current_active_user
from ....services.aps_integration import APSIntegration
from ....tasks.process_ifc import process_ifc_task
from ....core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aps", tags=["aps"])

# APS Configuration
APS_CLIENT_ID = os.getenv("APS_CLIENT_ID", "")
APS_CLIENT_SECRET = os.getenv("APS_CLIENT_SECRET", "")
APS_CALLBACK_URL = os.getenv("APS_CALLBACK_URL", "http://localhost:8000/api/v1/aps/callback")

if not APS_CLIENT_ID or not APS_CLIENT_SECRET:
    logger.warning("APS credentials not configured. APS integration will not be available.")

def get_aps_integration_for_user(user_id: int, db: Session) -> APSIntegration:
    """
    Get APS integration instance with loaded tokens for a user
    """
    if not APS_CLIENT_ID or not APS_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="APS integration not configured")
    
    aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
    
    if not aps.load_tokens_from_db(db, user_id):
        raise HTTPException(status_code=401, detail="APS authentication required")
    
    if not aps.is_token_valid():
        raise HTTPException(status_code=401, detail="APS token expired. Please re-authenticate")
    
    return aps

@router.get("/auth/login")
def aps_login(request: Request):
    """
    Initiate APS OAuth2 authentication
    """
    if not APS_CLIENT_ID or not APS_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="APS integration not configured")
    
    aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
    
    # Generate state parameter for security
    state = f"user_{request.state.user_id if hasattr(request.state, 'user_id') else 'anonymous'}"
    
    auth_url = aps.get_authorization_url(state=state)
    return {"auth_url": auth_url}

@router.get("/auth/callback")
def aps_callback(
    code: str, 
    state: str = None, 
    error: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Handle APS OAuth2 callback
    """
    if error:
        raise HTTPException(status_code=400, detail=f"APS authentication failed: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    try:
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        token_data = aps.exchange_code_for_token(code)
        
        # Store APS tokens in database
        aps.save_tokens_to_db(db, current_user.id)
        
        # Get user profile from APS
        user_profile = aps.get_user_profile()
        
        return {
            "message": "APS authentication successful",
            "user_profile": user_profile,
            "token_expires_in": token_data.get("expires_in")
        }
        
    except Exception as e:
        logger.error(f"Error in APS callback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete APS authentication: {str(e)}")

@router.post("/auth/logout")
def aps_logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout from APS and revoke tokens
    """
    try:
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        
        if aps.load_tokens_from_db(db, current_user.id):
            aps.revoke_tokens(db)
        
        return {"message": "APS logout successful"}
        
    except Exception as e:
        logger.error(f"Error in APS logout: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to logout from APS: {str(e)}")

@router.post("/auth/refresh")
def refresh_aps_token(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Refresh APS access token
    """
    try:
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        
        if not aps.load_tokens_from_db(db, current_user.id):
            raise HTTPException(status_code=401, detail="APS authentication required")
        
        token_data = aps.refresh_access_token()
        
        return {
            "message": "Token refreshed successfully",
            "expires_in": token_data.get("expires_in")
        }
        
    except Exception as e:
        logger.error(f"Error refreshing APS token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh APS token: {str(e)}")

@router.get("/hubs")
def get_aps_hubs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get list of APS hubs (teams/companies) user has access to
    """
    try:
        aps = get_aps_integration_for_user(current_user.id, db)
        hubs = aps.get_hubs()
        
        return {
            "hubs": [
                {
                    "id": hub["id"],
                    "name": hub["attributes"]["name"],
                    "type": hub["attributes"]["extension"]["type"],
                    "region": hub["attributes"]["region"]
                }
                for hub in hubs
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting APS hubs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get APS hubs: {str(e)}")

@router.get("/hubs/{hub_id}/projects")
def get_aps_projects(
    hub_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get list of projects in an APS hub
    """
    try:
        access_token = get_user_aps_token(current_user.id, db)
        
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        aps.set_token(access_token)
        
        projects = aps.get_projects(hub_id)
        
        return {
            "projects": [
                {
                    "id": project["id"],
                    "name": project["attributes"]["name"],
                    "status": project["attributes"]["status"],
                    "created_at": project["attributes"]["created_at"],
                    "updated_at": project["attributes"]["updated_at"]
                }
                for project in projects
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting APS projects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get APS projects: {str(e)}")

@router.get("/projects/{project_id}/contents")
def get_aps_project_contents(
    project_id: str,
    folder_id: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get contents of an APS project folder
    """
    try:
        access_token = get_user_aps_token(current_user.id, db)
        
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        aps.set_token(access_token)
        
        # Extract hub_id from project_id (format: b.{hub_id})
        hub_id = project_id.replace("b.", "")
        
        contents = aps.get_project_contents(hub_id, project_id, folder_id)
        
        return {
            "contents": [
                {
                    "id": item["id"],
                    "type": item["type"],
                    "name": item["attributes"]["displayName"],
                    "created_at": item["attributes"]["createTime"],
                    "updated_at": item["attributes"]["lastModifiedTime"],
                    "is_folder": item["type"] == "folders",
                    "extension": item["attributes"].get("extension", {}).get("type", ""),
                    "size": item["attributes"].get("storageSize", 0)
                }
                for item in contents
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting APS project contents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get APS project contents: {str(e)}")

@router.post("/projects/{project_id}/items/{item_id}/process")
def process_aps_model(
    project_id: str,
    item_id: str,
    version_id: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process an APS model through Vitruvius
    """
    try:
        access_token = get_user_aps_token(current_user.id, db)
        
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        aps.set_token(access_token)
        
        # Get item versions to find the URN
        versions = aps.get_item_versions(project_id, item_id)
        
        if not versions:
            raise HTTPException(status_code=404, detail="No versions found for this item")
        
        # Use specified version or latest
        if version_id:
            version = next((v for v in versions if v["id"] == version_id), None)
            if not version:
                raise HTTPException(status_code=404, detail="Version not found")
        else:
            version = versions[0]  # Latest version
        
        # Get the URN from the version
        urn = version["relationships"]["storage"]["data"]["id"]
        
        # Start translation to IFC
        translation_job = aps.translate_to_ifc(urn)
        
        # Create or get Vitruvius project
        vitruvius_project = create_or_get_vitruvius_project(
            project_id, 
            project_id,  # Use APS project ID as name for now
            current_user.id,
            db
        )
        
        # Create IFC model record
        ifc_model = IFCModel(
            project_id=vitruvius_project.id,
            filename=version["attributes"]["displayName"],
            file_path="",  # Will be set after download
            status="translating"
        )
        db.add(ifc_model)
        db.commit()
        db.refresh(ifc_model)
        
        # Start async task to monitor translation and process
        from ....tasks.aps_processor import process_aps_model_task
        task = process_aps_model_task.delay(
            urn, 
            vitruvius_project.id, 
            ifc_model.id,
            access_token
        )
        
        return {
            "message": "APS model processing started",
            "task_id": task.id,
            "model_id": ifc_model.id,
            "project_id": vitruvius_project.id,
            "translation_job": translation_job.get("urn", "")
        }
        
    except Exception as e:
        logger.error(f"Error processing APS model: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process APS model: {str(e)}")

@router.post("/projects/{project_id}/conflicts/{conflict_id}/create-issue")
def create_aps_issue(
    project_id: str,
    conflict_id: int,
    issue_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create an issue in APS (ACC/BIM 360) for a detected conflict
    """
    try:
        # Get the conflict
        conflict = db.query(Conflict).filter(
            Conflict.id == conflict_id,
            Conflict.project_id == project_id
        ).first()
        
        if not conflict:
            raise HTTPException(status_code=404, detail="Conflict not found")
        
        access_token = get_user_aps_token(current_user.id, db)
        
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        aps.set_token(access_token)
        
        # Prepare issue data
        aps_issue_data = {
            "title": f"Clash: {conflict.conflict_type} - {conflict.description}",
            "description": f"Conflict detected by Vitruvius AI:

{conflict.description}

Severity: {conflict.severity}
Status: {conflict.status}",
            "priority": "high" if conflict.severity == "high" else "normal",
            "issue_type_id": issue_data.get("issue_type_id", ""),
            "location_details": f"Conflict ID: {conflict.id}",
            "custom_attributes": [
                {
                    "name": "Vitruvius Conflict ID",
                    "value": str(conflict.id)
                },
                {
                    "name": "Conflict Type",
                    "value": conflict.conflict_type
                },
                {
                    "name": "Detection Method",
                    "value": "Vitruvius AI"
                }
            ]
        }
        
        # Add pushpin if location data is available
        if "pushpin" in issue_data:
            aps_issue_data["pushpin"] = issue_data["pushpin"]
        
        # Create the issue
        container_id = issue_data.get("container_id", project_id)
        issue = aps.create_issue(container_id, aps_issue_data)
        
        # Update conflict with APS issue ID
        conflict.aps_issue_id = issue["data"]["id"]
        db.commit()
        
        return {
            "message": "Issue created successfully in APS",
            "issue_id": issue["data"]["id"],
            "conflict_id": conflict.id
        }
        
    except Exception as e:
        logger.error(f"Error creating APS issue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create APS issue: {str(e)}")

@router.get("/projects/{project_id}/issues")
def get_aps_issues(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get issues from APS (ACC/BIM 360)
    """
    try:
        access_token = get_user_aps_token(current_user.id, db)
        
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        aps.set_token(access_token)
        
        # Get issues from APS
        issues = aps.get_issues(project_id)
        
        return {
            "issues": [
                {
                    "id": issue["id"],
                    "title": issue["attributes"]["title"],
                    "description": issue["attributes"]["description"],
                    "status": issue["attributes"]["status"],
                    "priority": issue["attributes"]["priority"],
                    "created_at": issue["attributes"]["createdAt"],
                    "created_by": issue["attributes"]["createdBy"],
                    "assigned_to": issue["attributes"]["assignedTo"],
                    "location_details": issue["attributes"]["locationDetails"]
                }
                for issue in issues
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting APS issues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get APS issues: {str(e)}")

def get_user_aps_token(user_id: int, db: Session) -> str:
    """
    Get user's APS access token from storage
    TODO: Implement proper token storage and retrieval
    """
    # This is a placeholder - in a real implementation, you'd store
    # APS tokens in a secure way (database, encrypted storage, etc.)
    # and handle token refresh automatically
    
    # For now, we'll raise an exception to indicate this needs to be implemented
    raise HTTPException(
        status_code=401, 
        detail="APS token not found. Please authenticate with APS first."
    )

def create_or_get_vitruvius_project(
    aps_project_id: str, 
    project_name: str, 
    user_id: int, 
    db: Session
) -> Project:
    """
    Create or get a Vitruvius project linked to an APS project
    """
    # Try to find existing project
    existing_project = db.query(Project).filter(
        Project.aps_project_id == aps_project_id,
        Project.owner_id == user_id
    ).first()
    
    if existing_project:
        return existing_project
    
    # Create new project
    new_project = Project(
        owner_id=user_id,
        name=f"APS: {project_name}",
        description=f"Project imported from Autodesk Platform Services: {aps_project_id}",
        aps_project_id=aps_project_id,
        status="created"
    )
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return new_project
