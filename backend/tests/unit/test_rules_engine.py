import pytest
from unittest.mock import Mock, patch
from app.services.rules_engine import (
    run_prescriptive_analysis,
    generate_solutions_for_conflict,
    calculate_cost_impact,
    calculate_time_impact,
    get_material_cost,
    get_labor_cost_per_hour,
    get_complexity_factor
)


class TestRulesEngine:
    """Test suite for the rules engine"""
    
    def test_run_prescriptive_analysis_with_valid_data(self):
        """Test prescriptive analysis with valid BIM data"""
        mock_bim_data = {
            "elements": [
                {
                    "global_id": "elem1",
                    "type": "IfcBeam",
                    "properties": {"material": "Steel"},
                    "has_geometry": True
                },
                {
                    "global_id": "elem2", 
                    "type": "IfcColumn",
                    "properties": {"material": "Concrete"},
                    "has_geometry": True
                }
            ]
        }
        
        result = run_prescriptive_analysis(mock_bim_data)
        
        assert "analysis_results" in result
        assert "metadata" in result
        assert isinstance(result["analysis_results"], list)
        assert result["metadata"]["total_elements"] == 2
        assert result["metadata"]["conflicts_analyzed"] > 0
    
    def test_run_prescriptive_analysis_with_empty_data(self):
        """Test prescriptive analysis with empty BIM data"""
        mock_bim_data = {"elements": []}
        
        result = run_prescriptive_analysis(mock_bim_data)
        
        assert result["analysis_results"] == []
        assert result["metadata"]["total_elements"] == 0
        assert result["metadata"]["conflicts_analyzed"] == 0
    
    def test_run_prescriptive_analysis_with_invalid_data(self):
        """Test prescriptive analysis with invalid BIM data"""
        mock_bim_data = {}
        
        result = run_prescriptive_analysis(mock_bim_data)
        
        assert result["analysis_results"] == []
        assert result["metadata"]["total_elements"] == 0
    
    def test_generate_solutions_for_beam_column_conflict(self):
        """Test solution generation for beam-column conflict"""
        mock_conflict = {
            "elements": ["elem1", "elem2"],
            "element_types": ["IfcBeam", "IfcColumn"],
            "severity": "high",
            "properties": [
                {"material": "Steel", "dimensions": "200x300"},
                {"material": "Concrete", "dimensions": "300x300"}
            ]
        }
        
        solutions = generate_solutions_for_conflict(mock_conflict)
        
        assert len(solutions) >= 2
        assert any(sol["type"] == "beam_adjustment" for sol in solutions)
        assert any(sol["type"] == "column_relocation" for sol in solutions)
        
        # Check that all solutions have required fields
        for solution in solutions:
            assert "type" in solution
            assert "description" in solution
            assert "estimated_cost" in solution
            assert "estimated_time" in solution
            assert solution["estimated_cost"] > 0
            assert solution["estimated_time"] > 0
    
    def test_generate_solutions_for_wall_column_conflict(self):
        """Test solution generation for wall-column conflict"""
        mock_conflict = {
            "elements": ["elem1", "elem2"],
            "element_types": ["IfcWall", "IfcColumn"],
            "severity": "medium",
            "properties": [
                {"material": "Concrete", "thickness": "200"},
                {"material": "Steel", "dimensions": "250x250"}
            ]
        }
        
        solutions = generate_solutions_for_conflict(mock_conflict)
        
        assert len(solutions) >= 2
        assert any(sol["type"] == "wall_opening" for sol in solutions)
        assert any(sol["type"] == "column_relocation" for sol in solutions)
    
    def test_calculate_cost_impact_beam_adjustment(self):
        """Test cost calculation for beam adjustment"""
        mock_conflict = {
            "element_types": ["IfcBeam", "IfcColumn"],
            "properties": [{"material": "Steel"}, {"material": "Concrete"}]
        }
        
        cost = calculate_cost_impact("beam_adjustment", mock_conflict)
        
        assert cost > 0
        assert isinstance(cost, (int, float))
    
    def test_calculate_cost_impact_column_relocation(self):
        """Test cost calculation for column relocation"""
        mock_conflict = {
            "element_types": ["IfcWall", "IfcColumn"],
            "properties": [{"material": "Concrete"}, {"material": "Steel"}]
        }
        
        cost = calculate_cost_impact("column_relocation", mock_conflict)
        
        assert cost > 0
        assert cost >= 5000  # Column relocation should be expensive
    
    def test_calculate_time_impact_beam_adjustment(self):
        """Test time calculation for beam adjustment"""
        mock_conflict = {
            "element_types": ["IfcBeam", "IfcColumn"],
            "severity": "high"
        }
        
        time = calculate_time_impact("beam_adjustment", mock_conflict)
        
        assert time > 0
        assert isinstance(time, (int, float))
    
    def test_calculate_time_impact_with_high_severity(self):
        """Test time calculation with high severity conflict"""
        mock_conflict = {
            "element_types": ["IfcBeam", "IfcColumn"],
            "severity": "high"
        }
        
        time_high = calculate_time_impact("structural_modification", mock_conflict)
        
        mock_conflict["severity"] = "low"
        time_low = calculate_time_impact("structural_modification", mock_conflict)
        
        assert time_high > time_low
    
    def test_get_material_cost_steel(self):
        """Test material cost calculation for steel"""
        cost = get_material_cost("Steel")
        assert cost == 800
    
    def test_get_material_cost_concrete(self):
        """Test material cost calculation for concrete"""
        cost = get_material_cost("Concrete")
        assert cost == 500
    
    def test_get_material_cost_unknown(self):
        """Test material cost calculation for unknown material"""
        cost = get_material_cost("UnknownMaterial")
        assert cost == 600  # Default cost
    
    def test_get_labor_cost_per_hour(self):
        """Test labor cost calculation"""
        cost = get_labor_cost_per_hour()
        assert cost == 50
        assert isinstance(cost, (int, float))
    
    def test_get_complexity_factor_high_severity(self):
        """Test complexity factor for high severity"""
        factor = get_complexity_factor("high")
        assert factor == 1.5
    
    def test_get_complexity_factor_medium_severity(self):
        """Test complexity factor for medium severity"""
        factor = get_complexity_factor("medium")
        assert factor == 1.2
    
    def test_get_complexity_factor_low_severity(self):
        """Test complexity factor for low severity"""
        factor = get_complexity_factor("low")
        assert factor == 1.0
    
    def test_get_complexity_factor_unknown_severity(self):
        """Test complexity factor for unknown severity"""
        factor = get_complexity_factor("unknown")
        assert factor == 1.0  # Default factor
    
    def test_solution_cost_consistency(self):
        """Test that solution costs are consistent and reasonable"""
        mock_conflict = {
            "elements": ["elem1", "elem2"],
            "element_types": ["IfcBeam", "IfcColumn"],
            "severity": "high",
            "properties": [
                {"material": "Steel"},
                {"material": "Concrete"}
            ]
        }
        
        solutions = generate_solutions_for_conflict(mock_conflict)
        
        # All solutions should have positive costs
        for solution in solutions:
            assert solution["estimated_cost"] > 0
            assert solution["estimated_time"] > 0
        
        # More complex solutions should generally cost more
        structural_solutions = [s for s in solutions if "structural" in s["type"]]
        if structural_solutions:
            for solution in structural_solutions:
                assert solution["estimated_cost"] >= 1000
    
    def test_multiple_conflicts_analysis(self):
        """Test analysis with multiple potential conflicts"""
        mock_bim_data = {
            "elements": [
                {
                    "global_id": "beam1",
                    "type": "IfcBeam",
                    "properties": {"material": "Steel"},
                    "has_geometry": True
                },
                {
                    "global_id": "column1",
                    "type": "IfcColumn", 
                    "properties": {"material": "Concrete"},
                    "has_geometry": True
                },
                {
                    "global_id": "wall1",
                    "type": "IfcWall",
                    "properties": {"material": "Concrete"},
                    "has_geometry": True
                },
                {
                    "global_id": "door1",
                    "type": "IfcDoor",
                    "properties": {"material": "Wood"},
                    "has_geometry": True
                }
            ]
        }
        
        result = run_prescriptive_analysis(mock_bim_data)
        
        assert len(result["analysis_results"]) >= 2
        assert result["metadata"]["total_elements"] == 4
        assert result["metadata"]["conflicts_analyzed"] >= 2
    
    @pytest.mark.parametrize("solution_type,expected_min_cost", [
        ("beam_adjustment", 1000),
        ("column_relocation", 5000),
        ("structural_modification", 3000),
        ("wall_opening", 800),
        ("door_relocation", 500)
    ])
    def test_solution_cost_ranges(self, solution_type, expected_min_cost):
        """Test that different solution types have appropriate cost ranges"""
        mock_conflict = {
            "element_types": ["IfcBeam", "IfcColumn"],
            "properties": [{"material": "Steel"}, {"material": "Concrete"}]
        }
        
        cost = calculate_cost_impact(solution_type, mock_conflict)
        assert cost >= expected_min_cost
    
    @pytest.mark.parametrize("solution_type,expected_min_time", [
        ("beam_adjustment", 1),
        ("column_relocation", 3),
        ("structural_modification", 2),
        ("wall_opening", 1),
        ("door_relocation", 1)
    ])
    def test_solution_time_ranges(self, solution_type, expected_min_time):
        """Test that different solution types have appropriate time ranges"""
        mock_conflict = {
            "element_types": ["IfcBeam", "IfcColumn"],
            "severity": "medium"
        }
        
        time = calculate_time_impact(solution_type, mock_conflict)
        assert time >= expected_min_time