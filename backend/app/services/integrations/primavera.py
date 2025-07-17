# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .base import PlanningIntegrationService, TaskUpdate, IntegrationResult, BaseIntegrationService


class PrimaveraService(PlanningIntegrationService, BaseIntegrationService):
    """Oracle Primavera P6 EPPM integration service"""
    
    def __init__(self, api_key: str, base_url: str, project_id: str, config: Optional[Dict] = None):
        super().__init__(api_key, base_url, project_id, config)
        self.session = requests.Session()
        self.session.headers.update(self.build_headers(api_key))
        
        # Primavera-specific configuration
        self.database_instance = config.get('database_instance', 1) if config else 1
        self.user_name = config.get('user_name', 'admin') if config else 'admin'
        
    def test_connection(self) -> IntegrationResult:
        """Test connection to Primavera P6 API"""
        try:
            # Test endpoint to verify API access
            response = self.session.get(f"{self.base_url}/api/DatabaseInstances")
            
            if response.status_code == 200:
                return IntegrationResult(
                    success=True,
                    message="Successfully connected to Primavera P6",
                    data=response.json()
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
        """Get project information from Primavera P6"""
        try:
            endpoint = f"{self.base_url}/api/DatabaseInstances/{self.database_instance}/Projects/{self.project_id}"
            response = self.session.get(endpoint)
            
            if response.status_code == 200:
                project_data = response.json()
                return IntegrationResult(
                    success=True,
                    message="Project information retrieved successfully",
                    data={
                        "project_name": project_data.get("Name"),
                        "start_date": project_data.get("PlannedStartDate"),
                        "finish_date": project_data.get("PlannedFinishDate"),
                        "status": project_data.get("Status"),
                        "currency": project_data.get("DefaultCurrency"),
                        "manager": project_data.get("ProjectManager")
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
        """Get all tasks/activities from Primavera P6 project"""
        try:
            endpoint = f"{self.base_url}/api/DatabaseInstances/{self.database_instance}/Projects/{self.project_id}/Activities"
            response = self.session.get(endpoint)
            
            if response.status_code == 200:
                activities = response.json()
                tasks = []
                
                for activity in activities:
                    tasks.append({
                        "id": activity.get("Id"),
                        "name": activity.get("Name"),
                        "type": activity.get("Type"),
                        "status": activity.get("Status"),
                        "planned_start": activity.get("PlannedStartDate"),
                        "planned_finish": activity.get("PlannedFinishDate"),
                        "actual_start": activity.get("ActualStartDate"),
                        "actual_finish": activity.get("ActualFinishDate"),
                        "duration": activity.get("PlannedDuration"),
                        "percent_complete": activity.get("PercentComplete"),
                        "budget_cost": activity.get("BudgetTotalCost"),
                        "actual_cost": activity.get("ActualTotalCost")
                    })
                
                return IntegrationResult(
                    success=True,
                    message=f"Retrieved {len(tasks)} tasks from Primavera",
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
        """Update a specific task/activity in Primavera P6"""
        try:
            endpoint = f"{self.base_url}/api/DatabaseInstances/{self.database_instance}/Projects/{self.project_id}/Activities/{task_update.task_id}"
            
            # Build update payload
            update_data = {}
            
            if task_update.name:
                update_data["Name"] = task_update.name
            
            if task_update.cost is not None:
                update_data["BudgetTotalCost"] = task_update.cost
            
            if task_update.duration_change_days is not None:
                # Convert days to Primavera duration format (typically in hours)
                update_data["PlannedDuration"] = task_update.duration_change_days * 8  # 8 hours per day
            
            if task_update.start_date:
                update_data["PlannedStartDate"] = task_update.start_date.isoformat()
            
            if task_update.end_date:
                update_data["PlannedFinishDate"] = task_update.end_date.isoformat()
            
            if task_update.progress_percentage is not None:
                update_data["PercentComplete"] = task_update.progress_percentage
            
            if task_update.notes:
                update_data["NotebookTopics"] = [{"Text": task_update.notes}]
            
            # Send update request
            response = self.session.patch(endpoint, json=update_data)
            
            if response.status_code in [200, 204]:
                return IntegrationResult(
                    success=True,
                    message=f"Task {task_update.task_id} updated successfully in Primavera",
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
        """Create a new task/activity in Primavera P6"""
        try:
            endpoint = f"{self.base_url}/api/DatabaseInstances/{self.database_instance}/Projects/{self.project_id}/Activities"
            
            # Build creation payload with required fields
            create_data = {
                "Id": task_update.task_id,
                "Name": task_update.name or "New Task from Vitruvius",
                "Type": "Task Dependent",  # Default activity type
                "Status": "Not Started"
            }
            
            if task_update.cost is not None:
                create_data["BudgetTotalCost"] = task_update.cost
            
            if task_update.duration_change_days is not None:
                create_data["PlannedDuration"] = task_update.duration_change_days * 8
            
            if task_update.start_date:
                create_data["PlannedStartDate"] = task_update.start_date.isoformat()
            
            if task_update.end_date:
                create_data["PlannedFinishDate"] = task_update.end_date.isoformat()
            
            # Send creation request
            response = self.session.post(endpoint, json=create_data)
            
            if response.status_code in [201, 200]:
                created_activity = response.json()
                return IntegrationResult(
                    success=True,
                    message=f"Task {task_update.task_id} created successfully in Primavera",
                    external_id=created_activity.get("Id"),
                    data=created_activity
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
        """Sync complete project schedule to Primavera P6"""
        try:
            results = []
            errors = []
            
            # Process each task in the schedule
            for task_data in schedule_data.get("tasks", []):
                task_update = TaskUpdate(
                    task_id=task_data.get("id"),
                    name=task_data.get("name"),
                    cost=task_data.get("cost"),
                    duration_change_days=task_data.get("duration_days"),
                    start_date=datetime.fromisoformat(task_data["start_date"]) if task_data.get("start_date") else None,
                    end_date=datetime.fromisoformat(task_data["end_date"]) if task_data.get("end_date") else None,
                    progress_percentage=task_data.get("progress")
                )
                
                # Try to update existing task, create if it doesn't exist
                result = self.update_task(task_update)
                if not result.success and "not found" in result.message.lower():
                    result = self.create_task(task_update)
                
                if result.success:
                    results.append(result)
                else:
                    errors.append(f"Task {task_update.task_id}: {result.message}")
            
            if errors:
                return IntegrationResult(
                    success=False,
                    message=f"Partial sync completed. {len(errors)} errors occurred: {'; '.join(errors[:3])}{'...' if len(errors) > 3 else ''}",
                    data={"successful": len(results), "failed": len(errors), "errors": errors}
                )
            else:
                return IntegrationResult(
                    success=True,
                    message=f"Successfully synced {len(results)} tasks to Primavera",
                    data={"synced_tasks": len(results)}
                )
                
        except Exception as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to sync project schedule: {str(e)}",
                error_code="SYNC_ERROR"
            )
    
    def get_cost_accounts(self) -> IntegrationResult:
        """Get cost accounts from Primavera for budget integration"""
        try:
            endpoint = f"{self.base_url}/api/DatabaseInstances/{self.database_instance}/CostAccounts"
            response = self.session.get(endpoint)
            
            if response.status_code == 200:
                cost_accounts = response.json()
                return IntegrationResult(
                    success=True,
                    message="Cost accounts retrieved successfully",
                    data={"cost_accounts": cost_accounts}
                )
            else:
                return self.handle_api_error(response, "get cost accounts")
                
        except requests.exceptions.RequestException as e:
            return IntegrationResult(
                success=False,
                message=f"Failed to get cost accounts: {str(e)}",
                error_code="API_ERROR"
            )