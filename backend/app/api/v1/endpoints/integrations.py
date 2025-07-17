# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import json
from datetime import datetime

from ...db.database import get_db
from ...auth.dependencies import get_current_active_user
from ...db.models.project import User, Project
from ...services.integration_factory import IntegrationFactory
from ...services.integrations.base import BaseIntegrationService
from ...services.feedback_service import IntegrationSyncService

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/available")
def get_available_integrations(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get list of available integration tools"""
    return {
        "planning_tools": IntegrationFactory.get_available_planning_integrations(),
        "budget_tools": IntegrationFactory.get_available_budget_integrations()
    }


@router.get("/projects/{project_id}/config")
def get_project_integration_config(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get integration configuration for a project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Parse JSON configs
    planning_config = {}
    budget_config = {}
    
    if project.planning_tool_config:
        try:
            planning_config = json.loads(project.planning_tool_config)
        except json.JSONDecodeError:
            planning_config = {}
    
    if project.budget_tool_config:
        try:
            budget_config = json.loads(project.budget_tool_config)
        except json.JSONDecodeError:
            budget_config = {}
    
    return {
        "project_id": project_id,
        "planning_tool": {
            "connected": project.planning_tool_connected,
            "project_id": project.planning_tool_project_id,
            "base_url": project.planning_tool_base_url,
            "config": planning_config,
            "has_api_key": bool(project.planning_tool_api_key)
        },
        "budget_tool": {
            "connected": project.budget_tool_connected,
            "project_id": project.budget_tool_project_id,
            "base_url": project.budget_tool_base_url,
            "config": budget_config,
            "has_api_key": bool(project.budget_tool_api_key)
        },
        "sync_status": project.sync_status,
        "last_sync_at": project.last_sync_at,
        "sync_error_message": project.sync_error_message
    }


@router.post("/projects/{project_id}/planning/configure")
def configure_planning_integration(
    project_id: int,
    config_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Configure planning tool integration for a project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate required fields
    required_fields = ["integration_type", "api_key", "project_id"]
    missing_fields = [field for field in required_fields if field not in config_data]
    if missing_fields:
        raise HTTPException(
            status_code=400, 
            detail=f"Missing required fields: {', '.join(missing_fields)}"
        )
    
    integration_type = config_data["integration_type"]
    additional_config = config_data.get("config", {})
    
    # Validate integration type and configuration
    is_valid, error_message = IntegrationFactory.validate_integration_config(
        integration_type, additional_config
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
    # Encrypt and store the API key
    encrypted_key = BaseIntegrationService.encrypt_api_key(config_data["api_key"])
    
    # Update project with integration configuration
    project.planning_tool_connected = integration_type
    project.planning_tool_api_key = encrypted_key
    project.planning_tool_project_id = config_data["project_id"]
    project.planning_tool_base_url = config_data.get("base_url", "")
    project.planning_tool_config = json.dumps(additional_config) if additional_config else None
    project.sync_status = "not_configured"
    project.sync_error_message = None
    
    db.commit()
    db.refresh(project)
    
    return {
        "message": f"Planning tool {integration_type} configured successfully",
        "integration_type": integration_type,
        "project_id": project_id,
        "sync_status": project.sync_status
    }


@router.post("/projects/{project_id}/budget/configure")
def configure_budget_integration(
    project_id: int,
    config_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Configure budget tool integration for a project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate required fields
    required_fields = ["integration_type", "api_key", "project_id"]
    missing_fields = [field for field in required_fields if field not in config_data]
    if missing_fields:
        raise HTTPException(
            status_code=400, 
            detail=f"Missing required fields: {', '.join(missing_fields)}"
        )
    
    integration_type = config_data["integration_type"]
    additional_config = config_data.get("config", {})
    
    # Validate integration type and configuration
    is_valid, error_message = IntegrationFactory.validate_integration_config(
        integration_type, additional_config
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
    # Check if integration is implemented
    available_budget_tools = IntegrationFactory.get_available_budget_integrations()
    if (integration_type not in available_budget_tools or 
        available_budget_tools[integration_type].get("status") == "planned"):
        raise HTTPException(
            status_code=400, 
            detail=f"Budget tool {integration_type} is not yet implemented"
        )
    
    # Encrypt and store the API key
    encrypted_key = BaseIntegrationService.encrypt_api_key(config_data["api_key"])
    
    # Update project with integration configuration
    project.budget_tool_connected = integration_type
    project.budget_tool_api_key = encrypted_key
    project.budget_tool_project_id = config_data["project_id"]
    project.budget_tool_base_url = config_data.get("base_url", "")
    project.budget_tool_config = json.dumps(additional_config) if additional_config else None
    
    db.commit()
    db.refresh(project)
    
    return {
        "message": f"Budget tool {integration_type} configured successfully",
        "integration_type": integration_type,
        "project_id": project_id
    }


@router.post("/projects/{project_id}/test")
def test_project_integrations(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Test all configured integrations for a project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Trigger async integration test
    sync_service = IntegrationSyncService(db)
    task = sync_service.test_integrations(project_id)
    
    if task:
        return {
            "message": "Integration test started",
            "task_id": task.id,
            "project_id": project_id
        }
    else:
        # If Celery is not available, test synchronously
        results = {}
        
        # Test planning tool
        if project.planning_tool_connected:
            services = IntegrationFactory.create_integration_from_project({
                'planning_tool_connected': project.planning_tool_connected,
                'planning_tool_api_key': project.planning_tool_api_key,
                'planning_tool_base_url': project.planning_tool_base_url,
                'planning_tool_project_id': project.planning_tool_project_id,
                'planning_tool_config': project.planning_tool_config
            })
            
            planning_service = services.get('planning')
            if planning_service:
                test_result = planning_service.test_connection()
                results['planning'] = {
                    "success": test_result.success,
                    "message": test_result.message,
                    "data": test_result.data
                }
            else:
                results['planning'] = {
                    "success": False,
                    "message": f"Failed to create {project.planning_tool_connected} service"
                }
        
        # Test budget tool
        if project.budget_tool_connected:
            results['budget'] = {
                "success": False,
                "message": f"Budget tool {project.budget_tool_connected} not yet implemented"
            }
        
        return {
            "message": "Integration test completed",
            "results": results,
            "project_id": project_id
        }


@router.post("/projects/{project_id}/sync/schedule")
def trigger_schedule_sync(
    project_id: int,
    schedule_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger synchronization of project schedule to planning tool"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.planning_tool_connected:
        raise HTTPException(
            status_code=400, 
            detail="No planning tool configured for this project"
        )
    
    # Trigger async schedule sync
    sync_service = IntegrationSyncService(db)
    sync_service.trigger_project_schedule_sync(project_id, schedule_data)
    
    return {
        "message": "Schedule synchronization started",
        "project_id": project_id,
        "integration_type": project.planning_tool_connected
    }


@router.post("/projects/{project_id}/sync/conflict/{conflict_id}")
def trigger_conflict_sync(
    project_id: int,
    conflict_id: int,
    solution_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger synchronization of conflict resolution to external tools"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify conflict exists in project
    from ...db.models.project import Conflict
    conflict = db.query(Conflict).filter(
        Conflict.id == conflict_id,
        Conflict.project_id == project_id
    ).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Trigger async conflict resolution sync
    sync_service = IntegrationSyncService(db)
    sync_service.trigger_conflict_resolution_sync(conflict_id, solution_data)
    
    return {
        "message": "Conflict resolution synchronization started",
        "project_id": project_id,
        "conflict_id": conflict_id,
        "planning_tool": project.planning_tool_connected,
        "budget_tool": project.budget_tool_connected
    }


@router.delete("/projects/{project_id}/planning")
def remove_planning_integration(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Remove planning tool integration from a project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Clear planning tool configuration
    project.planning_tool_connected = None
    project.planning_tool_api_key = None
    project.planning_tool_project_id = None
    project.planning_tool_base_url = None
    project.planning_tool_config = None
    project.sync_status = "not_configured"
    project.sync_error_message = None
    project.last_sync_at = None
    
    db.commit()
    
    return {
        "message": "Planning tool integration removed successfully",
        "project_id": project_id
    }


@router.delete("/projects/{project_id}/budget")
def remove_budget_integration(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Remove budget tool integration from a project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Clear budget tool configuration
    project.budget_tool_connected = None
    project.budget_tool_api_key = None
    project.budget_tool_project_id = None
    project.budget_tool_base_url = None
    project.budget_tool_config = None
    
    db.commit()
    
    return {
        "message": "Budget tool integration removed successfully",
        "project_id": project_id
    }