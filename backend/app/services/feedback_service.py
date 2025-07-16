# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from sqlalchemy.orm import Session
from ..db.models.project import Conflict, SolutionFeedback, Solution, Element
from ..db.models.analytics import HistoricalConflict

class FeedbackDataCollector:
    """Service to collect and store feedback data for ML training"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def collect_feedback_data(self, feedback: SolutionFeedback):
        """
        Extract and store historical conflict data from feedback for ML training
        """
        # Get the conflict and its associated elements
        conflict = self.db.query(Conflict).filter(Conflict.id == feedback.conflict_id).first()
        if not conflict:
            return
        
        # Get the elements involved in the conflict
        elements = conflict.elements
        if len(elements) < 2:
            return  # Need at least 2 elements for meaningful analysis
        
        # Extract element categories and disciplines
        element_1 = elements[0]
        element_2 = elements[1]
        
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
                if solution.estimated_cost:
                    resolution_cost = solution.estimated_cost / 100.0  # Convert from cents
                resolution_time_days = solution.estimated_time
        
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