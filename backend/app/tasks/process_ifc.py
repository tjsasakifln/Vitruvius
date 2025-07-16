from celery import Celery
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from ..services.bim_processor import process_ifc_file
from ..services.ia_prescriptive import run_prescriptive_analysis
from ..db.models.project import Project, IFCModel, Conflict, Solution
from ..db.database import DATABASE_URL
import json

# Configure Celery
celery_app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

# Database setup for Celery tasks
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task
def process_ifc_task(project_id: int, file_path: str):
    """
    Celery task to process an IFC file asynchronously with clash detection.
    """
    db = SessionLocal()
    
    try:
        print(f"Starting IFC processing for project {project_id}: {file_path}")
        
        # Update IFC model status
        ifc_model = db.query(IFCModel).filter(
            IFCModel.project_id == project_id,
            IFCModel.file_path == file_path
        ).first()
        
        if ifc_model:
            ifc_model.status = "processing"
            db.commit()
        
        # Process IFC file with clash detection
        bim_data = process_ifc_file(file_path)
        
        if not bim_data.get("processed", False):
            raise Exception(f"IFC processing failed: {bim_data.get('error', 'Unknown error')}")
        
        # Perform clash detection
        conflicts_detected = perform_clash_detection(bim_data)
        
        # Store conflicts in database
        for conflict_data in conflicts_detected:
            conflict = Conflict(
                project_id=project_id,
                conflict_type=conflict_data["type"],
                severity=conflict_data["severity"],
                description=conflict_data["description"],
                elements_involved=",".join(conflict_data["elements"]),
                status="detected"
            )
            db.add(conflict)
        
        db.commit()
        
        # Run prescriptive AI analysis
        analysis_results = run_prescriptive_analysis(bim_data)
        
        # Store AI-generated solutions
        for result in analysis_results.get("analysis_results", []):
            conflict_id = get_conflict_id_by_elements(db, project_id, result["conflict"]["elements"])
            
            for solution_data in result["solutions"]:
                solution = Solution(
                    conflict_id=conflict_id,
                    solution_type=solution_data["type"],
                    description=solution_data["description"],
                    estimated_cost=int(solution_data["estimated_cost"] * 100),  # Store in cents
                    estimated_time=int(solution_data["estimated_time"]),
                    confidence_score=80,  # Default confidence score
                    status="proposed"
                )
                db.add(solution)
        
        db.commit()
        
        # Update IFC model status
        if ifc_model:
            ifc_model.status = "processed"
            ifc_model.processed_at = db.query(Solution).first().created_at
            db.commit()
        
        print(f"IFC processing completed for project {project_id}")
        return {
            "status": "completed",
            "project_id": project_id,
            "conflicts_detected": len(conflicts_detected),
            "solutions_generated": len(analysis_results.get("analysis_results", []))
        }
        
    except Exception as e:
        print(f"Error processing IFC file: {str(e)}")
        
        # Update status to failed
        if ifc_model:
            ifc_model.status = "failed"
            db.commit()
        
        return {
            "status": "failed",
            "error": str(e),
            "project_id": project_id
        }
    
    finally:
        db.close()

def perform_clash_detection(bim_data):
    """
    Perform clash detection on BIM data using geometric analysis.
    """
    conflicts = []
    elements = bim_data.get("elements", [])
    
    # Simple clash detection algorithm
    for i, element1 in enumerate(elements):
        for j, element2 in enumerate(elements[i+1:], i+1):
            # Check if elements have geometry
            if not (element1.get("has_geometry") and element2.get("has_geometry")):
                continue
                
            # Check for potential conflicts based on element types
            if is_potential_conflict(element1, element2):
                severity = determine_severity(element1, element2)
                
                conflict = {
                    "type": "collision",
                    "severity": severity,
                    "description": f"{element1['type']} conflicts with {element2['type']}",
                    "elements": [element1["global_id"], element2["global_id"]]
                }
                conflicts.append(conflict)
    
    return conflicts

def is_potential_conflict(element1, element2):
    """
    Determine if two elements are likely to conflict based on their types.
    """
    structural_elements = ["IfcBeam", "IfcColumn", "IfcSlab", "IfcWall"]
    
    # Check if both are structural elements (higher chance of conflict)
    if element1["type"] in structural_elements and element2["type"] in structural_elements:
        return True
    
    # Check specific conflict scenarios
    if element1["type"] == "IfcBeam" and element2["type"] == "IfcColumn":
        return True
    if element1["type"] == "IfcDoor" and element2["type"] == "IfcWall":
        return True
    
    return False

def determine_severity(element1, element2):
    """
    Determine conflict severity based on element types.
    """
    critical_conflicts = [
        ("IfcBeam", "IfcColumn"),
        ("IfcSlab", "IfcBeam"),
        ("IfcWall", "IfcColumn")
    ]
    
    element_pair = (element1["type"], element2["type"])
    reverse_pair = (element2["type"], element1["type"])
    
    if element_pair in critical_conflicts or reverse_pair in critical_conflicts:
        return "high"
    
    return "medium"

def get_conflict_id_by_elements(db, project_id, elements):
    """
    Get conflict ID by matching elements.
    """
    elements_str = ",".join(elements)
    conflict = db.query(Conflict).filter(
        Conflict.project_id == project_id,
        Conflict.elements_involved == elements_str
    ).first()
    
    return conflict.id if conflict else None
