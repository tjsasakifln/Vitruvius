# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .base import PlanningIntegrationService, TaskUpdate, IntegrationResult, BaseIntegrationService


class MSProjectService(PlanningIntegrationService, BaseIntegrationService):
    """Microsoft Project Online / Project for the Web integration service"""
    
    def __init__(self, api_key: str, base_url: str, project_id: str, config: Optional[Dict] = None):
        super().__init__(api_key, base_url, project_id, config)
        self.session = requests.Session()
        
        # MS Project uses OAuth2, so api_key should be access token
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Vitruvius-Integration/1.0"
        })
        
        # MS Project specific configuration
        self.tenant_id = config.get('tenant_id') if config else None
        self.site_url = config.get('site_url', 'https://graph.microsoft.com/v1.0') if config else 'https://graph.microsoft.com/v1.0'
        
    def test_connection(self) -> IntegrationResult:
        """Test connection to Microsoft Project API"""
        try:
            # Test with a simple API call to get user info
            response = self.session.get(f"{self.site_url}/me")
            
            if response.status_code == 200:
                user_data = response.json()
                return IntegrationResult(
                    success=True,
                    message="Successfully connected to Microsoft Project",
                    data={
                        "user": user_data.get("displayName"),
                        "email": user_data.get("mail")
                    }
                )
            else:
                return self.handle_api_error(response, "test connection")
                
        except requests.exceptions.RequestException as e:
            return IntegrationResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                error_code="CONNECTION_ERROR"
            )
    
    def get_project_info(self) -> IntegrationResult:
        """Get project information from Microsoft Project"""
        try:
            # For Project for the Web, use the Planner API
            endpoint = f"{self.site_url}/planner/plans/{self.project_id}"
            response = self.session.get(endpoint)
            
            if response.status_code == 200:
                project_data = response.json()
                return IntegrationResult(
                    success=True,
                    message="Project information retrieved successfully",
                    data={
                        "project_name": project_data.get("title"),
                        "created_date": project_data.get("createdDateTime"),
                        "owner": project_data.get("owner"),
                        "container_id": project_data.get("container", {}).get("containerId")
                    }
                )
            else:
                return self.handle_api_error(response, "get project info")
                
        except requests.exceptions.RequestException as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to get project info: {str(e)}",
                error_code="API_ERROR"
            )
    
    def get_tasks(self) -> IntegrationResult:
        """Get all tasks from Microsoft Project"""
        try:
            # Get tasks from the plan
            endpoint = f"{self.site_url}/planner/plans/{self.project_id}/tasks"
            response = self.session.get(endpoint)
            
            if response.status_code == 200:
                tasks_data = response.json()
                tasks = []
                
                for task in tasks_data.get("value", []):
                    tasks.append({
                        "id": task.get("id"),
                        "name": task.get("title"),
                        "description": task.get("description"),
                        "start_date": task.get("startDateTime"),
                        "due_date": task.get("dueDateTime"),
                        "percent_complete": task.get("percentComplete", 0),
                        "priority": task.get("priority", 5),
                        "bucket_id": task.get("bucketId"),
                        "assigned_to": [assignment.get("userId") for assignment in task.get("assignments", {}).values()],
                        "created_date": task.get("createdDateTime"),
                        "completed_date": task.get("completedDateTime")
                    })
                
                return IntegrationResult(
                    success=True,
                    message=f"Retrieved {len(tasks)} tasks from Microsoft Project",
                    data={"tasks": tasks}
                )
            else:
                return self.handle_api_error(response, "get tasks")
                
        except requests.exceptions.RequestException as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to get tasks: {str(e)}",
                error_code="API_ERROR"
            )
    
    def update_task(self, task_update: TaskUpdate) -> IntegrationResult:
        """Update a specific task in Microsoft Project"""
        try:
            endpoint = f"{self.site_url}/planner/tasks/{task_update.task_id}"
            
            # First get the current task to get the @odata.etag for optimistic concurrency
            current_task_response = self.session.get(endpoint)
            if current_task_response.status_code != 200:
                return self.handle_api_error(current_task_response, "get current task for update")
            
            current_task = current_task_response.json()
            etag = current_task.get("@odata.etag")
            
            # Build update payload
            update_data = {}
            
            if task_update.name:
                update_data["title"] = task_update.name
            
            if task_update.start_date:
                update_data["startDateTime"] = task_update.start_date.isoformat()
            
            if task_update.end_date:
                update_data["dueDateTime"] = task_update.end_date.isoformat()
            
            if task_update.progress_percentage is not None:
                update_data["percentComplete"] = int(task_update.progress_percentage)
            
            if task_update.notes:
                update_data["description"] = task_update.notes
            
            # MS Project requires If-Match header for updates
            headers = self.session.headers.copy()
            if etag:
                headers["If-Match"] = etag
            
            # Send update request
            response = self.session.patch(endpoint, json=update_data, headers=headers)
            
            if response.status_code in [200, 204]:
                return IntegrationResult(
                    success=True,
                    message=f"Task {task_update.task_id} updated successfully in Microsoft Project",
                    external_id=task_update.task_id,
                    data=update_data
                )
            else:
                return self.handle_api_error(response, "update task")
                
        except requests.exceptions.RequestException as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to update task: {str(e)}",
                error_code="API_ERROR"
            )
    
    def create_task(self, task_update: TaskUpdate) -> IntegrationResult:
        """Create a new task in Microsoft Project"""
        try:
            endpoint = f"{self.site_url}/planner/tasks"
            
            # Build creation payload with required fields
            create_data = {
                "planId": self.project_id,
                "title": task_update.name or "New Task from Vitruvius"
            }
            
            if task_update.start_date:
                create_data["startDateTime"] = task_update.start_date.isoformat()
            
            if task_update.end_date:
                create_data["dueDateTime"] = task_update.end_date.isoformat()
            
            if task_update.notes:
                create_data["description"] = task_update.notes
            
            if task_update.progress_percentage is not None:
                create_data["percentComplete"] = int(task_update.progress_percentage)
            
            # Send creation request
            response = self.session.post(endpoint, json=create_data)
            
            if response.status_code in [201, 200]:
                created_task = response.json()
                return IntegrationResult(
                    success=True,
                    message=f"Task created successfully in Microsoft Project",
                    external_id=created_task.get("id"),
                    data=created_task
                )
            else:
                return self.handle_api_error(response, "create task")
                
        except requests.exceptions.RequestException as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to create task: {str(e)}",
                error_code="API_ERROR"
            )
    
    def sync_project_schedule(self, schedule_data: Dict[str, Any]) -> IntegrationResult:
        """Sync complete project schedule to Microsoft Project"""
        try:
            results = []
            errors = []
            
            # Process each task in the schedule
            for task_data in schedule_data.get("tasks", []):
                task_update = TaskUpdate(
                    task_id=task_data.get("id"),
                    name=task_data.get("name"),
                    start_date=datetime.fromisoformat(task_data["start_date"]) if task_data.get("start_date") else None,
                    end_date=datetime.fromisoformat(task_data["end_date"]) if task_data.get("end_date") else None,
                    progress_percentage=task_data.get("progress"),
                    notes=task_data.get("description")
                )
                
                # Try to update existing task, create if it doesn't exist
                result = self.update_task(task_update)
                if not result.success and "not found" in result.message.lower():
                    result = self.create_task(task_update)
                
                if result.success:
                    results.append(result)
                else:
                    errors.append(f"Task {task_update.task_id or 'new'}: {result.message}")
            
            if errors:
                return IntegrationResult(
                    success=False,
                    message=f"Partial sync completed. {len(errors)} errors occurred: {'; '.join(errors[:3])}{'...' if len(errors) > 3 else ''}",
                    data={"successful": len(results), "failed": len(errors), "errors": errors}
                )
            else:
                return IntegrationResult(
                    success=True,
                    message=f"Successfully synced {len(results)} tasks to Microsoft Project",
                    data={"synced_tasks": len(results)}
                )
                
        except Exception as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to sync project schedule: {str(e)}",
                error_code="SYNC_ERROR"
            )
    
    def get_buckets(self) -> IntegrationResult:
        """Get buckets (task groups) from Microsoft Project plan"""
        try:
            endpoint = f"{self.site_url}/planner/plans/{self.project_id}/buckets"
            response = self.session.get(endpoint)
            
            if response.status_code == 200:
                buckets_data = response.json()
                buckets = []
                
                for bucket in buckets_data.get("value", []):
                    buckets.append({
                        "id": bucket.get("id"),
                        "name": bucket.get("name"),
                        "plan_id": bucket.get("planId"),
                        "order_hint": bucket.get("orderHint")
                    })
                
                return IntegrationResult(
                    success=True,
                    message="Buckets retrieved successfully",
                    data={"buckets": buckets}
                )
            else:
                return self.handle_api_error(response, "get buckets")
                
        except requests.exceptions.RequestException as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to get buckets: {str(e)}",
                error_code="API_ERROR"
            )
    
    def create_bucket(self, bucket_name: str) -> IntegrationResult:
        """Create a new bucket (task group) in Microsoft Project"""
        try:
            endpoint = f"{self.site_url}/planner/buckets"
            
            create_data = {
                "name": bucket_name,
                "planId": self.project_id
            }
            
            response = self.session.post(endpoint, json=create_data)
            
            if response.status_code in [201, 200]:
                created_bucket = response.json()
                return IntegrationResult(
                    success=True,
                    message=f"Bucket '{bucket_name}' created successfully",
                    external_id=created_bucket.get("id"),
                    data=created_bucket
                )
            else:
                return self.handle_api_error(response, "create bucket")
                
        except requests.exceptions.RequestException as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to create bucket: {str(e)}",
                error_code="API_ERROR"
            )