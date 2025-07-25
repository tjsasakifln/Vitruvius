# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from ..db.models.project import Conflict, SolutionFeedback, Solution, Element, Project
from ..db.models.analytics import HistoricalConflict

logger = logging.getLogger(__name__)

class FeedbackDataCollector:
    """Service to collect and store feedback data for ML training"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def collect_feedback_data(self, feedback: SolutionFeedback):
        """
        Extract and store historical conflict data from feedback for ML training
        """
        # Validate input feedback
        if not feedback:
            logger.warning("Feedback is None, cannot collect data")
            return
        
        if not feedback.conflict_id:
            logger.warning("Feedback has no conflict_id, cannot collect data")
            return
        
        # Get the conflict and its associated elements
        conflict = self.db.query(Conflict).filter(Conflict.id == feedback.conflict_id).first()
        if not conflict:
            logger.warning(f"Conflict not found for feedback {feedback.id}")
            return
        
        # Get the elements involved in the conflict
        elements = conflict.elements
        if not elements:
            logger.warning(f"Conflict {conflict.id} has no elements, cannot collect feedback data")
            return
        
        if len(elements) < 2:
            logger.warning(f"Conflict {conflict.id} has fewer than 2 elements, cannot collect feedback data")
            return
        
        # Safely extract element categories and disciplines
        element_1 = elements[0]
        element_2 = elements[1]
        
        # Validate elements are not None
        if not element_1 or not element_2:
            logger.warning(f"One or both elements are None for conflict {conflict.id}")
            return
        
        # Validate elements have required attributes
        if not hasattr(element_1, 'element_type') or not hasattr(element_2, 'element_type'):
            logger.warning(f"Elements missing element_type attribute for conflict {conflict.id}")
            return
        
        if not element_1.element_type or not element_2.element_type:
            logger.warning(f"Elements have empty element_type for conflict {conflict.id}")
            return
        
        # Determine if feedback is positive based on effectiveness rating
        feedback_positive = False
        if feedback.effectiveness_rating and feedback.effectiveness_rating >= 4:
            feedback_positive = True
        elif feedback.feedback_type == "selected_suggested" and feedback.solution_id:
            # If they selected a suggested solution, consider it positive
            feedback_positive = True
        
        # Get solution cost and time if available
        resolution_cost = None
        resolution_time_days = None
        
        if feedback.solution_id:
            solution = self.db.query(Solution).filter(Solution.id == feedback.solution_id).first()
            if solution:
                # Safely extract cost with null checks
                if solution.estimated_cost is not None and solution.estimated_cost > 0:
                    resolution_cost = solution.estimated_cost / 100.0  # Convert from cents
                else:
                    logger.info(f"Solution {solution.id} has no valid estimated_cost")
                
                # Safely extract time with null checks
                if solution.estimated_time is not None and solution.estimated_time > 0:
                    resolution_time_days = solution.estimated_time
                else:
                    logger.info(f"Solution {solution.id} has no valid estimated_time")
            else:
                logger.warning(f"Solution not found for ID {feedback.solution_id}")
        
        # Create historical conflict record
        historical_conflict = HistoricalConflict(
            project_id=conflict.project_id,
            element_category_1=element_1.element_type,
            element_category_2=element_2.element_type,
            discipline_1=self._extract_discipline(element_1.element_type),
            discipline_2=self._extract_discipline(element_2.element_type),
            conflict_type=conflict.conflict_type,
            severity=conflict.severity,
            resolution_cost=resolution_cost,
            resolution_time_days=resolution_time_days,
            solution_feedback_positive=feedback_positive,
            effectiveness_rating=feedback.effectiveness_rating
        )
        
        self.db.add(historical_conflict)
        self.db.commit()
        
        # Trigger integration sync if feedback indicates a solution was implemented
        if feedback_positive and feedback.solution_id:
            # Only trigger if solution was found
            if 'solution' in locals() and solution:
                self._trigger_integration_sync(feedback, solution)
            else:
                logger.warning(f"Cannot trigger integration sync: solution not found for feedback {feedback.id}")
        
        return historical_conflict
    
    def _extract_discipline(self, element_type: str) -> str:
        """
        Extract discipline from element type based on IFC conventions
        """
        element_type_lower = element_type.lower()
        
        if any(x in element_type_lower for x in ['wall', 'slab', 'column', 'beam', 'foundation']):
            return "Structural"
        elif any(x in element_type_lower for x in ['door', 'window', 'furniture', 'space']):
            return "Architectural"
        elif any(x in element_type_lower for x in ['pipe', 'duct', 'equipment', 'fitting']):
            return "MEP"
        elif any(x in element_type_lower for x in ['railing', 'stair', 'ramp']):
            return "Circulation"
        else:
            return "Other"
    
    def _trigger_integration_sync(self, feedback: SolutionFeedback, solution: Optional[Solution]):
        """
        Trigger async integration sync when a solution is implemented
        """
        # Validate input parameters
        if not feedback:
            logger.warning("Feedback is None, cannot trigger integration sync")
            return
        
        if not feedback.conflict_id:
            logger.warning("Feedback has no conflict_id, cannot trigger integration sync")
            return
        
        try:
            from ..tasks.integration_tasks import sync_to_planning_tool, sync_to_budget_tool
            
            # Get the conflict and project with null checks
            conflict = self.db.query(Conflict).filter(Conflict.id == feedback.conflict_id).first()
            if not conflict:
                logger.warning(f"Conflict not found for feedback {feedback.id}")
                return
            
            if not conflict.project_id:
                logger.warning(f"Conflict {conflict.id} has no project_id")
                return
            
            project = self.db.query(Project).filter(Project.id == conflict.project_id).first()
            if not project:
                logger.warning(f"Project not found for conflict {conflict.id}")
                return
            
            # Prepare task update data for planning tool sync
            task_update_data = {
                'task_id': f"conflict_{conflict.id}",
                'name': f"Resolve {conflict.conflict_type} Conflict",
                'notes': f"Solution implemented based on user feedback: {feedback.implementation_notes or 'No additional notes'}",
                'status': 'in_progress' if feedback.effectiveness_rating and feedback.effectiveness_rating >= 4 else 'needs_attention'
            }
            
            # Add cost information if available with null checks
            if solution and solution.estimated_cost is not None and solution.estimated_cost > 0:
                task_update_data['cost'] = solution.estimated_cost / 100.0  # Convert from cents
                
                # Prepare cost update data for budget tool sync
                conflict_type = conflict.conflict_type or "unknown"
                cost_update_data = {
                    'cost_category': f"{conflict_type}_resolution",
                    'amount': solution.estimated_cost / 100.0,
                    'description': f"Cost for resolving {conflict_type} conflict",
                    'budget_code': f"CONFLICT_{conflict.id}",
                    'effective_date': datetime.utcnow().isoformat()
                }
                
                # Trigger budget sync if budget tool is configured
                if hasattr(project, 'budget_tool_connected') and project.budget_tool_connected:
                    sync_to_budget_tool.delay(
                        project_id=project.id,
                        cost_update_data=cost_update_data,
                        conflict_id=conflict.id
                    )
                else:
                    logger.info(f"Budget tool not connected for project {project.id}")
            
            # Add time information if available with null checks
            if solution and solution.estimated_time is not None and solution.estimated_time > 0:
                task_update_data['duration_change_days'] = solution.estimated_time
                task_update_data['start_date'] = datetime.utcnow().isoformat()
                task_update_data['end_date'] = (datetime.utcnow() + timedelta(days=solution.estimated_time)).isoformat()
            else:
                logger.info(f"No valid estimated_time found for solution {solution.id if solution else 'None'}")
            
            # Set progress based on feedback effectiveness
            if feedback.effectiveness_rating:
                if feedback.effectiveness_rating >= 4:
                    task_update_data['progress_percentage'] = 25.0  # Started implementation
                elif feedback.effectiveness_rating <= 2:
                    task_update_data['progress_percentage'] = 0.0  # Solution not working
                else:
                    task_update_data['progress_percentage'] = 10.0  # Under review
            
            # Trigger planning tool sync if planning tool is configured
            if hasattr(project, 'planning_tool_connected') and project.planning_tool_connected:
                sync_to_planning_tool.delay(
                    project_id=project.id,
                    task_update_data=task_update_data,
                    conflict_id=conflict.id
                )
            else:
                logger.info(f"Planning tool not connected for project {project.id}")
                
        except ImportError:
            # Celery tasks not available (e.g., in testing)
            pass
        except Exception as e:
            # Log error but don't fail the feedback collection
            logger.error(f"Error triggering integration sync: {str(e)}", exc_info=True)


class IntegrationSyncService:
    """Service to handle integration synchronization triggers"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def trigger_conflict_resolution_sync(self, conflict_id: int, solution_data: Dict[str, Any]):
        """
        Trigger sync when a conflict resolution is started or updated
        
        Args:
            conflict_id: ID of the conflict being resolved
            solution_data: Dictionary containing solution implementation details
        """
        try:
            from ..tasks.integration_tasks import sync_to_planning_tool, sync_to_budget_tool
            
            conflict = self.db.query(Conflict).filter(Conflict.id == conflict_id).first()
            if not conflict:
                logger.warning(f"Conflict not found for ID {conflict_id}")
                return
            
            if not conflict.project_id:
                logger.warning(f"Conflict {conflict_id} has no project_id")
                return
            
            project = self.db.query(Project).filter(Project.id == conflict.project_id).first()
            if not project:
                logger.warning(f"Project not found for conflict {conflict_id}")
                return
            
            # Prepare task update data
            task_update_data = {
                'task_id': solution_data.get('task_id', f"conflict_{conflict_id}"),
                'name': solution_data.get('name', f"Resolve {conflict.conflict_type} Conflict"),
                'notes': solution_data.get('notes', ''),
                'status': solution_data.get('status', 'in_progress'),
                'cost': solution_data.get('cost'),
                'duration_change_days': solution_data.get('duration_days'),
                'start_date': solution_data.get('start_date'),
                'end_date': solution_data.get('end_date'),
                'progress_percentage': solution_data.get('progress_percentage', 0.0)
            }
            
            # Trigger planning tool sync
            if project.planning_tool_connected:
                sync_to_planning_tool.delay(
                    project_id=project.id,
                    task_update_data=task_update_data,
                    conflict_id=conflict_id
                )
            
            # Trigger budget tool sync if cost data is provided
            if solution_data.get('cost') and project.budget_tool_connected:
                cost_update_data = {
                    'cost_category': solution_data.get('cost_category', f"{conflict.conflict_type}_resolution"),
                    'amount': solution_data['cost'],
                    'description': solution_data.get('cost_description', f"Cost for resolving {conflict.conflict_type} conflict"),
                    'budget_code': solution_data.get('budget_code', f"CONFLICT_{conflict_id}"),
                    'effective_date': solution_data.get('effective_date', datetime.utcnow().isoformat())
                }
                
                sync_to_budget_tool.delay(
                    project_id=project.id,
                    cost_update_data=cost_update_data,
                    conflict_id=conflict_id
                )
                
        except ImportError:
            # Celery tasks not available
            pass
        except Exception as e:
            print(f"Error triggering conflict resolution sync: {str(e)}")
    
    def trigger_project_schedule_sync(self, project_id: int, schedule_data: Optional[Dict[str, Any]] = None):
        """
        Trigger sync of complete project schedule
        
        Args:
            project_id: ID of the project
            schedule_data: Optional schedule data to sync
        """
        try:
            from ..tasks.integration_tasks import sync_complete_project_schedule
            
            sync_complete_project_schedule.delay(
                project_id=project_id,
                schedule_data=schedule_data
            )
            
        except ImportError:
            # Celery tasks not available
            pass
        except Exception as e:
            print(f"Error triggering project schedule sync: {str(e)}")
    
    def test_integrations(self, project_id: int):
        """
        Test all configured integrations for a project
        
        Args:
            project_id: ID of the project to test
        """
        try:
            from ..tasks.integration_tasks import test_integration_connection
            
            return test_integration_connection.delay(project_id)
            
        except ImportError:
            # Celery tasks not available
            return None
        except Exception as e:
            print(f"Error triggering integration test: {str(e)}")
            return None