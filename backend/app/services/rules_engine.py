# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from typing import Dict, List, Any
import json
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class RulesEngine:
    """Advanced rules engine for BIM conflict resolution"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
        self.cost_factors = self._initialize_cost_factors()
        self.time_factors = self._initialize_time_factors()
    
    def _initialize_rules(self) -> Dict[str, Any]:
        """Initialize comprehensive rule set for conflict resolution"""
        return {
            "collision": {
                "beam_column": {
                    "solutions": [
                        {
                            "type": "beam_relocation",
                            "description": "Relocate beam to avoid column intersection",
                            "priority": 1,
                            "base_cost_impact": 0.12,
                            "base_time_impact": 0.08,
                            "feasibility": 0.9
                        },
                        {
                            "type": "column_adjustment",
                            "description": "Adjust column position or size",
                            "priority": 2,
                            "base_cost_impact": 0.18,
                            "base_time_impact": 0.15,
                            "feasibility": 0.7
                        },
                        {
                            "type": "structural_redesign",
                            "description": "Redesign structural system",
                            "priority": 3,
                            "base_cost_impact": 0.35,
                            "base_time_impact": 0.25,
                            "feasibility": 0.6
                        }
                    ]
                },
                "wall_beam": {
                    "solutions": [
                        {
                            "type": "beam_elevation_change",
                            "description": "Modify beam elevation to clear wall",
                            "priority": 1,
                            "base_cost_impact": 0.08,
                            "base_time_impact": 0.05,
                            "feasibility": 0.85
                        },
                        {
                            "type": "wall_opening",
                            "description": "Create opening in wall for beam passage",
                            "priority": 2,
                            "base_cost_impact": 0.15,
                            "base_time_impact": 0.10,
                            "feasibility": 0.8
                        }
                    ]
                },
                "generic": {
                    "solutions": [
                        {
                            "type": "element_relocation",
                            "description": "Relocate one of the conflicting elements",
                            "priority": 1,
                            "base_cost_impact": 0.15,
                            "base_time_impact": 0.10,
                            "feasibility": 0.8
                        },
                        {
                            "type": "geometric_modification",
                            "description": "Modify element geometry to resolve conflict",
                            "priority": 2,
                            "base_cost_impact": 0.20,
                            "base_time_impact": 0.15,
                            "feasibility": 0.7
                        }
                    ]
                }
            },
            "clearance": {
                "insufficient_spacing": {
                    "solutions": [
                        {
                            "type": "spacing_optimization",
                            "description": "Optimize spacing between elements",
                            "priority": 1,
                            "base_cost_impact": 0.05,
                            "base_time_impact": 0.03,
                            "feasibility": 0.9
                        },
                        {
                            "type": "element_resizing",
                            "description": "Resize elements to improve clearance",
                            "priority": 2,
                            "base_cost_impact": 0.12,
                            "base_time_impact": 0.08,
                            "feasibility": 0.75
                        }
                    ]
                }
            }
        }
    
    def _initialize_cost_factors(self) -> Dict[str, float]:
        """Initialize cost factors based on element types and project context"""
        return {
            "IfcBeam": 1.2,
            "IfcColumn": 1.5,
            "IfcWall": 0.8,
            "IfcSlab": 1.1,
            "IfcDoor": 0.6,
            "IfcWindow": 0.7,
            "default": 1.0
        }
    
    def _initialize_time_factors(self) -> Dict[str, float]:
        """Initialize time factors based on element types and project context"""
        return {
            "IfcBeam": 1.1,
            "IfcColumn": 1.3,
            "IfcWall": 0.9,
            "IfcSlab": 1.2,
            "IfcDoor": 0.7,
            "IfcWindow": 0.8,
            "default": 1.0
        }

class PrescriptiveAnalysis:
    """AI-powered prescriptive analysis engine for BIM conflicts"""
    
    def __init__(self):
        self.rules_engine = RulesEngine()
        self.base_project_cost = 100000  # Base project cost in currency units
        self.base_project_time = 60  # Base project time in days
    
    def analyze_conflicts(self, bim_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze BIM data and generate prescriptive solutions"""
        logger.info("Starting prescriptive analysis of BIM data")
        
        # Extract detected conflicts from BIM data
        conflicts = self._extract_conflicts_from_bim_data(bim_data)
        analysis_results = []
        
        for conflict in conflicts:
            logger.info(f"Analyzing conflict: {conflict['id']}")
            
            # Generate contextual solutions
            solutions = self._generate_contextual_solutions(conflict, bim_data)
            
            # Rank solutions by multiple criteria
            ranked_solutions = self._rank_solutions_advanced(solutions, conflict)
            
            analysis_results.append({
                "conflict": conflict,
                "solutions": ranked_solutions,
                "recommended_solution": ranked_solutions[0] if ranked_solutions else None,
                "analysis_confidence": self._calculate_analysis_confidence(conflict, solutions)
            })
        
        logger.info(f"Prescriptive analysis completed for {len(conflicts)} conflicts")
        return analysis_results
    
    def _extract_conflicts_from_bim_data(self, bim_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract conflicts from processed BIM data"""
        # This method would typically receive conflicts from the clash detection phase
        # For now, we'll extract elements and simulate conflicts
        elements = bim_data.get("elements", [])
        conflicts = []
        
        # Generate mock conflicts based on element combinations
        for i, element1 in enumerate(elements[:5]):  # Limit for demo
            for element2 in elements[i+1:6]:
                if self._elements_likely_conflict(element1, element2):
                    conflict = {
                        "id": f"conflict_{i}_{i+1}",
                        "type": "collision",
                        "severity": self._determine_conflict_severity(element1, element2),
                        "elements": [element1.get("global_id", f"elem_{i}"), element2.get("global_id", f"elem_{i+1}")],
                        "element_types": [element1.get("type", "Unknown"), element2.get("type", "Unknown")],
                        "description": f"{element1.get('type', 'Element')} conflicts with {element2.get('type', 'Element')}"
                    }
                    conflicts.append(conflict)
        
        return conflicts
    
    def _elements_likely_conflict(self, element1: Dict, element2: Dict) -> bool:
        """Determine if two elements are likely to conflict"""
        structural_elements = ["IfcBeam", "IfcColumn", "IfcSlab", "IfcWall"]
        type1 = element1.get("type", "")
        type2 = element2.get("type", "")
        
        return (type1 in structural_elements and type2 in structural_elements) or \
               (type1 == "IfcBeam" and type2 == "IfcColumn")
    
    def _determine_conflict_severity(self, element1: Dict, element2: Dict) -> str:
        """Determine conflict severity based on element types"""
        critical_pairs = [("IfcBeam", "IfcColumn"), ("IfcSlab", "IfcBeam")]
        type1 = element1.get("type", "")
        type2 = element2.get("type", "")
        
        if (type1, type2) in critical_pairs or (type2, type1) in critical_pairs:
            return "high"
        return "medium"
    
    def _generate_contextual_solutions(self, conflict: Dict[str, Any], bim_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate solutions based on conflict context and rules engine"""
        conflict_type = conflict["type"]
        element_types = conflict.get("element_types", [])
        
        # Determine specific rule set to use
        rule_key = self._get_rule_key(conflict_type, element_types)
        rules = self.rules_engine.rules.get(conflict_type, {}).get(rule_key, 
                self.rules_engine.rules.get(conflict_type, {}).get("generic", {}))
        
        base_solutions = rules.get("solutions", [])
        enhanced_solutions = []
        
        for solution in base_solutions:
            enhanced_solution = self._enhance_solution_with_context(solution, conflict, bim_data)
            enhanced_solutions.append(enhanced_solution)
        
        return enhanced_solutions
    
    def _get_rule_key(self, conflict_type: str, element_types: List[str]) -> str:
        """Determine the appropriate rule key based on element types"""
        if len(element_types) >= 2:
            type1, type2 = element_types[0].lower(), element_types[1].lower()
            
            if "beam" in type1 and "column" in type2:
                return "beam_column"
            elif "beam" in type2 and "column" in type1:
                return "beam_column"
            elif "wall" in type1 and "beam" in type2:
                return "wall_beam"
            elif "wall" in type2 and "beam" in type1:
                return "wall_beam"
        
        return "generic"
    
    def _enhance_solution_with_context(self, solution: Dict[str, Any], conflict: Dict[str, Any], bim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance solution with project-specific context and calculations"""
        element_types = conflict.get("element_types", [])
        
        # Calculate cost and time impacts with element-specific factors
        cost_factor = self._get_element_factor(element_types, self.rules_engine.cost_factors)
        time_factor = self._get_element_factor(element_types, self.rules_engine.time_factors)
        
        estimated_cost = self.base_project_cost * solution["base_cost_impact"] * cost_factor
        estimated_time = self.base_project_time * solution["base_time_impact"] * time_factor
        
        # Apply severity multiplier
        severity_multiplier = {"high": 1.3, "medium": 1.0, "low": 0.8}.get(conflict.get("severity", "medium"), 1.0)
        
        enhanced_solution = {
            **solution,
            "conflict_id": conflict["id"],
            "estimated_cost": estimated_cost * severity_multiplier,
            "estimated_time": estimated_time * severity_multiplier,
            "feasibility_score": solution.get("feasibility", 0.8),
            "complexity_score": self._calculate_complexity_score(solution, conflict),
            "impact_assessment": self._generate_impact_assessment(solution, conflict)
        }
        
        return enhanced_solution
    
    def _get_element_factor(self, element_types: List[str], factors: Dict[str, float]) -> float:
        """Get average factor for involved element types"""
        if not element_types:
            return factors.get("default", 1.0)
        
        total_factor = sum(factors.get(elem_type, factors.get("default", 1.0)) for elem_type in element_types)
        return total_factor / len(element_types)
    
    def _calculate_complexity_score(self, solution: Dict[str, Any], conflict: Dict[str, Any]) -> float:
        """Calculate solution complexity based on multiple factors"""
        base_complexity = 1.0 - solution.get("feasibility", 0.8)
        severity_impact = {"high": 0.3, "medium": 0.2, "low": 0.1}.get(conflict.get("severity", "medium"), 0.2)
        
        return min(base_complexity + severity_impact, 1.0)
    
    def _generate_impact_assessment(self, solution: Dict[str, Any], conflict: Dict[str, Any]) -> Dict[str, str]:
        """Generate human-readable impact assessment"""
        cost_impact = "High" if solution["estimated_cost"] > self.base_project_cost * 0.2 else \
                     "Medium" if solution["estimated_cost"] > self.base_project_cost * 0.1 else "Low"
        
        time_impact = "High" if solution["estimated_time"] > self.base_project_time * 0.2 else \
                     "Medium" if solution["estimated_time"] > self.base_project_time * 0.1 else "Low"
        
        return {
            "cost_impact": cost_impact,
            "time_impact": time_impact,
            "overall_disruption": "High" if cost_impact == "High" or time_impact == "High" else 
                                "Medium" if cost_impact == "Medium" or time_impact == "Medium" else "Low"
        }
    
    def _rank_solutions_advanced(self, solutions: List[Dict[str, Any]], conflict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Advanced solution ranking considering multiple criteria"""
        def solution_score(solution):
            # Multi-criteria scoring
            cost_score = 1.0 / (1.0 + solution["estimated_cost"] / self.base_project_cost)
            time_score = 1.0 / (1.0 + solution["estimated_time"] / self.base_project_time)
            feasibility_score = solution.get("feasibility_score", 0.8)
            complexity_score = 1.0 - solution.get("complexity_score", 0.5)
            priority_score = 1.0 / solution.get("priority", 1)
            
            # Weighted combination
            total_score = (cost_score * 0.25 + time_score * 0.25 + 
                          feasibility_score * 0.30 + complexity_score * 0.10 + 
                          priority_score * 0.10)
            
            return total_score
        
        return sorted(solutions, key=solution_score, reverse=True)
    
    def _calculate_analysis_confidence(self, conflict: Dict[str, Any], solutions: List[Dict[str, Any]]) -> float:
        """Calculate confidence in the analysis results"""
        if not solutions:
            return 0.0
        
        # Factors affecting confidence
        solution_count_factor = min(len(solutions) / 3.0, 1.0)  # More solutions = higher confidence
        feasibility_factor = sum(s.get("feasibility_score", 0.8) for s in solutions) / len(solutions)
        severity_confidence = {"high": 0.9, "medium": 0.8, "low": 0.7}.get(conflict.get("severity", "medium"), 0.8)
        
        return (solution_count_factor * 0.3 + feasibility_factor * 0.4 + severity_confidence * 0.3)

def run_prescriptive_analysis(bim_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to run prescriptive analysis"""
    analyzer = PrescriptiveAnalysis()
    results = analyzer.analyze_conflicts(bim_data)
    
    return {
        "status": "completed",
        "conflicts_found": len(results),
        "analysis_results": results
    }


# New database-driven functions for adaptive solutions
def suggest_solutions_for_conflict(conflict_id: int, project_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Suggest solutions for a specific conflict, prioritized by confidence score
    """
    from ..db.models.project import Solution, Conflict
    
    # Get the conflict
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not conflict:
        logger.warning(f"Conflict not found for ID {conflict_id}")
        return []
    
    # Validate conflict has required attributes
    if not conflict.conflict_type:
        logger.warning(f"Conflict {conflict_id} has no conflict_type")
        return []
    
    # Get existing solutions for this conflict type, ordered by confidence
    solutions = db.query(Solution).join(Conflict).filter(
        Conflict.conflict_type == conflict.conflict_type,
        Conflict.project_id == project_id
    ).order_by(Solution.confidence_score.desc()).all()
    
    # Check if solutions query returned valid results
    if not solutions:
        logger.info(f"No solutions found for conflict type {conflict.conflict_type} in project {project_id}")
        return []
    
    # Convert to dictionaries for response
    solution_suggestions = []
    for solution in solutions:
        solution_dict = {
            "id": solution.id,
            "type": solution.solution_type,
            "description": solution.description,
            "estimated_cost": solution.estimated_cost / 100.0 if solution.estimated_cost else None,
            "estimated_time": solution.estimated_time,
            "confidence_score": solution.confidence_score,
            "status": solution.status,
            "created_at": solution.created_at
        }
        solution_suggestions.append(solution_dict)
    
    return solution_suggestions


def calculate_solution_cost_with_project_params(solution_data: Dict[str, Any], project_id: int, db: Session) -> float:
    """
    Calculate solution cost using project-specific cost parameters
    """
    from ..db.models.project import ProjectCost
    
    # Validate input parameters
    if not solution_data:
        logger.warning("Solution data is None or empty, using default cost")
        return 1000.0
    
    if not isinstance(solution_data, dict):
        logger.error(f"Solution data must be a dictionary, got {type(solution_data)}")
        return 1000.0
    
    # Get project cost parameters
    project_costs = db.query(ProjectCost).filter(ProjectCost.project_id == project_id).all()
    
    # Validate project costs query result
    if project_costs is None:
        logger.warning(f"No project costs found for project {project_id}")
        project_costs = []
    
    # Build cost map with null checks
    cost_map = {}
    for cost in project_costs:
        if cost and cost.parameter_name and cost.cost is not None:
            cost_map[cost.parameter_name] = cost.cost
        else:
            logger.warning(f"Invalid cost record found: {cost}")
    
    # Default cost factors if not specified in project
    default_costs = {
        "CONCRETE_M3": 500.0,
        "STEEL_KG": 2.5,
        "LABOR_HOUR": 45.0,
        "EQUIPMENT_HOUR": 75.0,
        "MATERIAL_TRANSPORT": 150.0
    }
    
    # Calculate cost based on solution type and parameters
    solution_type = solution_data.get("type", "")
    base_cost = 0.0
    
    if "relocation" in solution_type.lower():
        labor_cost = cost_map.get("LABOR_HOUR", default_costs["LABOR_HOUR"])
        equipment_cost = cost_map.get("EQUIPMENT_HOUR", default_costs["EQUIPMENT_HOUR"])
        base_cost = (labor_cost * 8) + (equipment_cost * 2)  # 8 hours labor + 2 hours equipment
        
    elif "redesign" in solution_type.lower():
        labor_cost = cost_map.get("LABOR_HOUR", default_costs["LABOR_HOUR"])
        base_cost = labor_cost * 24  # 24 hours for redesign work
        
    elif "modification" in solution_type.lower() or "adjustment" in solution_type.lower():
        labor_cost = cost_map.get("LABOR_HOUR", default_costs["LABOR_HOUR"])
        material_cost = cost_map.get("MATERIAL_TRANSPORT", default_costs["MATERIAL_TRANSPORT"])
        base_cost = (labor_cost * 4) + material_cost  # 4 hours labor + material transport
        
    else:
        # Generic solution cost
        labor_cost = cost_map.get("LABOR_HOUR", default_costs["LABOR_HOUR"])
        base_cost = labor_cost * 6  # 6 hours for generic solution
    
    # Apply complexity multiplier based on confidence score
    confidence_score = solution_data.get("confidence_score", 1.0)
    
    # Validate confidence score
    if confidence_score is None or not isinstance(confidence_score, (int, float)):
        logger.warning(f"Invalid confidence score {confidence_score}, using default")
        confidence_score = 1.0
    
    # Ensure confidence score is within valid range
    confidence_score = max(0.1, min(confidence_score, 1.0))
    
    complexity_multiplier = 2.0 - confidence_score  # Lower confidence = higher cost
    
    # Validate final cost calculation
    final_cost = base_cost * complexity_multiplier
    
    if final_cost <= 0:
        logger.warning(f"Invalid final cost {final_cost}, using default")
        final_cost = 1000.0
    
    return final_cost


def create_solution_from_rules(conflict_id: int, solution_data: Dict[str, Any], project_id: int, db: Session) -> Dict[str, Any]:
    """
    Create a new solution in the database based on rules engine output
    """
    from ..db.models.project import Solution
    
    # Validate input parameters
    if not solution_data:
        logger.error("Solution data is None or empty")
        return {}
    
    if not isinstance(solution_data, dict):
        logger.error(f"Solution data must be a dictionary, got {type(solution_data)}")
        return {}
    
    # Calculate cost using project parameters
    estimated_cost = calculate_solution_cost_with_project_params(solution_data, project_id, db)
    
    # Validate estimated cost
    if estimated_cost is None or estimated_cost < 0:
        logger.warning(f"Invalid estimated cost {estimated_cost}, using default value")
        estimated_cost = 1000.0  # Default cost
    
    # Create solution record
    solution = Solution(
        conflict_id=conflict_id,
        solution_type=solution_data.get("type", "generic"),
        description=solution_data.get("description", ""),  # Fixed: was using 'solution' instead of 'solution_data'
        estimated_cost=int(estimated_cost * 100),  # Convert to cents
        estimated_time=solution_data.get("estimated_time", 5),
        confidence_score=solution_data.get("confidence_score", 1.0),
        status="proposed"
    )
    
    # Validate solution object before database operation
    if not solution.solution_type:
        logger.warning("Solution type is empty, using default")
        solution.solution_type = "generic"
    
    db.add(solution)
    db.commit()
    db.refresh(solution)
    
    return {
        "id": solution.id,
        "type": solution.solution_type,
        "description": solution.description,
        "estimated_cost": solution.estimated_cost / 100.0,
        "estimated_time": solution.estimated_time,
        "confidence_score": solution.confidence_score,
        "status": solution.status,
        "created_at": solution.created_at
    }