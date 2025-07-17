# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from celery import Celery
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

from ..db.database import get_db
from ..db.models.project import Project, Conflict, Solution
from ..services.integration_factory import IntegrationFactory
from ..services.integrations.base import TaskUpdate, CostUpdate, IntegrationResult

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Celery (this should match your existing Celery configuration)
try:
    from ..core.celery_app import celery_app
except ImportError:
    # Fallback for basic Celery setup if celery_app doesn't exist
    celery_app = Celery('vitruvius')


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_to_planning_tool(self, project_id: int, task_update_data: Dict[str, Any], conflict_id: Optional[int] = None):
    """
    Sync task updates to external planning tool
    
    Args:
        project_id: ID of the Vitruvius project
        task_update_data: Dictionary containing task update information
        conflict_id: Optional conflict ID that triggered this sync
    """
    try:
        # Get project with integration configuration
        with SessionLocal() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                logger.error(f"Project {project_id} not found")
                return {"success": False, "error": "Project not found"}
            
            # Check if planning tool is configured
            if not project.planning_tool_connected:
                logger.info(f"No planning tool configured for project {project_id}")
                return {"success": True, "message": "No planning tool configured"}
            
            # Update sync status
            project.sync_status = "syncing"
            db.commit()
            
            # Get project configuration for integration
            project_config = {
                'planning_tool_connected': project.planning_tool_connected,
                'planning_tool_api_key': project.planning_tool_api_key,
                'planning_tool_base_url': project.planning_tool_base_url,
                'planning_tool_project_id': project.planning_tool_project_id,
                'planning_tool_config': project.planning_tool_config
            }
        
        # Create integration service
        services = IntegrationFactory.create_integration_from_project(project_config)
        
        planning_service = services.get('planning')
        if not planning_service:
            error_msg = f"Failed to create planning service for {project_config['planning_tool_connected']}"
            logger.error(error_msg)
            with SessionLocal() as db:
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.sync_status = "error"
                    project.sync_error_message = error_msg
                    db.commit()
            return {"success": False, "error": error_msg}
        
        # Create TaskUpdate from the provided data
        task_update = TaskUpdate(
            task_id=task_update_data.get('task_id'),
            name=task_update_data.get('name'),
            cost=task_update_data.get('cost'),
            duration_change_days=task_update_data.get('duration_change_days'),
            start_date=datetime.fromisoformat(task_update_data['start_date']) if task_update_data.get('start_date') else None,
            end_date=datetime.fromisoformat(task_update_data['end_date']) if task_update_data.get('end_date') else None,
            status=task_update_data.get('status'),
            progress_percentage=task_update_data.get('progress_percentage'),
            notes=task_update_data.get('notes')
        )
        
        # Attempt to update the task
        result = planning_service.update_task(task_update)
        
        # If task doesn't exist, try to create it
        if not result.success and "not found" in result.message.lower():
            logger.info(f"Task {task_update.task_id} not found, attempting to create")
            result = planning_service.create_task(task_update)
        
        # Update project sync status based on result
        with SessionLocal() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                if result.success:
                    project.sync_status = "connected"
                    project.last_sync_at = datetime.utcnow()
                    project.sync_error_message = None
                    logger.info(f"Successfully synced task to {project.planning_tool_connected} for project {project_id}")
                else:
                    project.sync_status = "error"
                    project.sync_error_message = result.message
                    logger.error(f"Failed to sync task to {project.planning_tool_connected}: {result.message}")
                
                db.commit()
                
                return {
                    "success": result.success,
                    "message": result.message,
                    "external_id": result.external_id,
                    "integration_type": project.planning_tool_connected
                }
        
    except Exception as exc:
        logger.error(f"Error in sync_to_planning_tool: {str(exc)}")
        
        # Update project sync status on error
        try:
            with SessionLocal() as db:
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.sync_status = "error"
                    project.sync_error_message = str(exc)
                    db.commit()
        except:
            pass
        
        # Retry the task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task in {self.default_retry_delay} seconds (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=self.default_retry_delay, exc=exc)
        
        return {"success": False, "error": str(exc)}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_to_budget_tool(self, project_id: int, cost_update_data: Dict[str, Any], conflict_id: Optional[int] = None):
    """
    Sync cost updates to external budget tool
    
    Args:
        project_id: ID of the Vitruvius project
        cost_update_data: Dictionary containing cost update information
        conflict_id: Optional conflict ID that triggered this sync
    """
    try:
        # Get project with integration configuration
        with SessionLocal() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                logger.error(f"Project {project_id} not found")
                return {"success": False, "error": "Project not found"}
            
            # Check if budget tool is configured
            if not project.budget_tool_connected:
                logger.info(f"No budget tool configured for project {project_id}")
                return {"success": True, "message": "No budget tool configured"}
            
            # Get project configuration for integration
            project_config = {
                'budget_tool_connected': project.budget_tool_connected,
                'budget_tool_api_key': project.budget_tool_api_key,
                'budget_tool_base_url': project.budget_tool_base_url,
                'budget_tool_project_id': project.budget_tool_project_id,
                'budget_tool_config': project.budget_tool_config
            }
        
        # Create integration service
        services = IntegrationFactory.create_integration_from_project(project_config)
        
        budget_service = services.get('budget')
        if not budget_service:
            error_msg = f"Budget tool {project_config['budget_tool_connected']} not yet implemented"
            logger.warning(error_msg)
            return {"success": True, "message": error_msg}
        
        # Create CostUpdate from the provided data
        cost_update = CostUpdate(
            cost_category=cost_update_data.get('cost_category', 'General'),
            amount=cost_update_data.get('amount', 0),
            currency=cost_update_data.get('currency', 'USD'),
            description=cost_update_data.get('description'),
            budget_code=cost_update_data.get('budget_code'),
            effective_date=datetime.fromisoformat(cost_update_data['effective_date']) if cost_update_data.get('effective_date') else datetime.utcnow()
        )
        
        # Attempt to update the cost
        result = budget_service.update_cost(cost_update)
        
        # If cost entry doesn't exist, try to create it
        if not result.success and "not found" in result.message.lower():
            logger.info(f"Cost entry not found, attempting to create")
            result = budget_service.create_cost_entry(cost_update)
        
        if result.success:
            logger.info(f"Successfully synced cost to {project_config['budget_tool_connected']} for project {project_id}")
        else:
            logger.error(f"Failed to sync cost to {project_config['budget_tool_connected']}: {result.message}")
        
        return {
            "success": result.success,
            "message": result.message,
            "external_id": result.external_id,
            "integration_type": project_config['budget_tool_connected']
        }
        
    except Exception as exc:
        logger.error(f"Error in sync_to_budget_tool: {str(exc)}")
        
        # Retry the task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task in {self.default_retry_delay} seconds (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=self.default_retry_delay, exc=exc)
        
        return {"success": False, "error": str(exc)}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def sync_complete_project_schedule(self, project_id: int, schedule_data: Optional[Dict[str, Any]] = None):
    """
    Sync complete project schedule to external planning tool
    
    Args:
        project_id: ID of the Vitruvius project
        schedule_data: Optional schedule data, if not provided will be generated from conflicts
    """
    try:
        # Get project with integration configuration
        with SessionLocal() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                logger.error(f"Project {project_id} not found")
                return {"success": False, "error": "Project not found"}
            
            # Check if planning tool is configured
            if not project.planning_tool_connected:
                logger.info(f"No planning tool configured for project {project_id}")
                return {"success": True, "message": "No planning tool configured"}
            
            # Update sync status
            project.sync_status = "syncing"
            db.commit()
            
            # Get project configuration for integration
            project_config = {
                'planning_tool_connected': project.planning_tool_connected,
                'planning_tool_api_key': project.planning_tool_api_key,
                'planning_tool_base_url': project.planning_tool_base_url,
                'planning_tool_project_id': project.planning_tool_project_id,
                'planning_tool_config': project.planning_tool_config
            }
        
        # Create integration service
        services = IntegrationFactory.create_integration_from_project(project_config)
        
        planning_service = services.get('planning')
        if not planning_service:
            error_msg = f"Failed to create planning service for {project_config['planning_tool_connected']}"
            logger.error(error_msg)
            with SessionLocal() as db:
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.sync_status = "error"
                    project.sync_error_message = error_msg
                    db.commit()
            return {"success": False, "error": error_msg}
        
        # Generate schedule data from conflicts if not provided
        if not schedule_data:
            with SessionLocal() as db:
                schedule_data = generate_schedule_from_conflicts(db, project_id)
        
        # Sync the schedule
        result = planning_service.sync_project_schedule(schedule_data)
        
        # Update project sync status based on result
        with SessionLocal() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                if result.success:
                    project.sync_status = "connected"
                    project.last_sync_at = datetime.utcnow()
                    project.sync_error_message = None
                    logger.info(f"Successfully synced complete schedule to {project.planning_tool_connected} for project {project_id}")
                else:
                    project.sync_status = "error"
                    project.sync_error_message = result.message
                    logger.error(f"Failed to sync schedule to {project.planning_tool_connected}: {result.message}")
                
                db.commit()
        
        return {
            "success": result.success,
            "message": result.message,
            "integration_type": project_config['planning_tool_connected'],
            "synced_data": result.data
        }
        
    except Exception as exc:
        logger.error(f"Error in sync_complete_project_schedule: {str(exc)}")
        
        # Update project sync status on error
        try:
            with SessionLocal() as db:
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.sync_status = "error"
                    project.sync_error_message = str(exc)
                    db.commit()
        except:
            pass
        
        # Retry the task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task in {self.default_retry_delay} seconds (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=self.default_retry_delay, exc=exc)
        
        return {"success": False, "error": str(exc)}


@celery_app.task
def test_integration_connection(project_id: int):
    """
    Test connection to external integration tools
    
    Args:
        project_id: ID of the Vitruvius project
    """
    try:
        # Get project with integration configuration
        with SessionLocal() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"success": False, "error": "Project not found"}
        
        results = {}
        
        # Test planning tool connection
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
                results['planning'] = planning_service.test_connection()
            else:
                results['planning'] = IntegrationResult(
                    success=False,
                    message=f"Failed to create {project.planning_tool_connected} service"
                )
        
        # Test budget tool connection
        if project.budget_tool_connected:
            services = IntegrationFactory.create_integration_from_project({
                'budget_tool_connected': project.budget_tool_connected,
                'budget_tool_api_key': project.budget_tool_api_key,
                'budget_tool_base_url': project.budget_tool_base_url,
                'budget_tool_project_id': project.budget_tool_project_id,
                'budget_tool_config': project.budget_tool_config
            })
            
            budget_service = services.get('budget')
            if budget_service:
                results['budget'] = budget_service.test_connection()
            else:
                results['budget'] = IntegrationResult(
                    success=False,
                    message=f"Budget tool {project.budget_tool_connected} not yet implemented"
                )
        
        return {
            "success": True,
            "results": {
                key: {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data
                } for key, result in results.items()
            }
        }
        
    except Exception as exc:
        logger.error(f"Error in test_integration_connection: {str(exc)}")
        return {"success": False, "error": str(exc)}


def generate_schedule_from_conflicts(db: Session, project_id: int) -> Dict[str, Any]:
    """
    Generate schedule data from project conflicts and solutions
    
    Args:
        db: Database session
        project_id: Project ID
        
    Returns:
        Dictionary with schedule data for external sync
    """
    conflicts = db.query(Conflict).filter(Conflict.project_id == project_id).all()
    tasks = []
    
    for conflict in conflicts:
        # Create a task for conflict resolution
        task_data = {
            "id": f"conflict_{conflict.id}",
            "name": f"Resolve {conflict.conflict_type} Conflict",
            "description": conflict.description,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + datetime.timedelta(days=7)).isoformat(),  # Default 7 days
            "progress": 0
        }
        
        # Add cost information from solutions if available
        solutions = db.query(Solution).filter(Solution.conflict_id == conflict.id).all()
        if solutions:
            best_solution = max(solutions, key=lambda s: s.confidence_score)
            if best_solution.estimated_cost:
                task_data["cost"] = best_solution.estimated_cost / 100.0  # Convert from cents
            if best_solution.estimated_time:
                task_data["duration_days"] = best_solution.estimated_time
                task_data["end_date"] = (datetime.utcnow() + datetime.timedelta(days=best_solution.estimated_time)).isoformat()
        
        tasks.append(task_data)
    
    return {"tasks": tasks}