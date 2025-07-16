from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from datetime import datetime
from ...db.models.project import Project, IFCModel, Conflict, User, Solution, SolutionFeedback
from ...db.database import get_db
from ...services.bim_processor import process_ifc_file
from ...tasks.process_ifc import process_ifc_task
from ...auth.dependencies import get_current_active_user

router = APIRouter(prefix="/projects", tags=["projects"])

# Ensure upload directory exists
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/", response_model=List[dict])
def get_projects(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all projects for current user"""
    projects = db.query(Project).filter(Project.owner_id == current_user.id).all()
    return [{"id": p.id, "name": p.name, "status": p.status, "created_at": p.created_at} for p in projects]


@router.post("/", response_model=dict)
def create_project(
    project_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new project"""
    project = Project(
        owner_id=current_user.id,
        name=project_data.get("name"),
        description=project_data.get("description", ""),
        status="created"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "status": project.status}


@router.post("/{project_id}/upload-ifc")
async def upload_ifc_model(
    project_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload IFC model to project"""
    if not file.filename.endswith('.ifc'):
        raise HTTPException(status_code=400, detail="File must be IFC format")
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file to disk
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Create IFC model record
    ifc_model = IFCModel(
        project_id=project_id,
        filename=file.filename,
        file_path=file_path,
        status="uploaded"
    )
    db.add(ifc_model)
    db.commit()
    db.refresh(ifc_model)
    
    # Start async processing
    task = process_ifc_task.delay(project_id, file_path)
    
    return {
        "message": "IFC file uploaded successfully",
        "task_id": task.id,
        "model_id": ifc_model.id,
        "file_path": file_path
    }


@router.get("/{project_id}/conflicts")
def get_project_conflicts(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conflicts detected in project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get real conflicts from database
    conflicts = db.query(Conflict).filter(Conflict.project_id == project_id).all()
    
    return {
        "project_id": project_id,
        "conflicts": [
            {
                "id": c.id,
                "type": c.conflict_type,
                "description": c.description,
                "severity": c.severity,
                "elements": [{"id": e.id, "ifc_id": e.ifc_id, "type": e.element_type, "name": e.name} for e in c.elements],
                "status": c.status,
                "created_at": c.created_at
            }
            for c in conflicts
        ]
    }


@router.get("/{project_id}/conflicts/{conflict_id}/solutions")
def get_conflict_solutions(
    project_id: int,
    conflict_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get solutions for a specific conflict"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get conflict and its solutions
    conflict = db.query(Conflict).filter(
        Conflict.id == conflict_id,
        Conflict.project_id == project_id
    ).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    solutions = db.query(Solution).filter(Solution.conflict_id == conflict_id).all()
    
    return {
        "conflict_id": conflict_id,
        "solutions": [
            {
                "id": s.id,
                "type": s.solution_type,
                "description": s.description,
                "estimated_cost": s.estimated_cost / 100.0 if s.estimated_cost else None,  # Convert from cents
                "estimated_time": s.estimated_time,
                "confidence_score": s.confidence_score,
                "status": s.status,
                "created_at": s.created_at
            }
            for s in solutions
        ]
    }


@router.post("/{project_id}/conflicts/{conflict_id}/feedback")
def submit_solution_feedback(
    project_id: int,
    conflict_id: int,
    feedback_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit feedback about conflict solution"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify conflict exists
    conflict = db.query(Conflict).filter(
        Conflict.id == conflict_id,
        Conflict.project_id == project_id
    ).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Validate feedback data
    feedback_type = feedback_data.get("feedback_type")
    if feedback_type not in ["selected_suggested", "custom_solution"]:
        raise HTTPException(status_code=400, detail="Invalid feedback type")
    
    solution_id = feedback_data.get("solution_id")
    if feedback_type == "selected_suggested" and not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID required for selected_suggested feedback")
    
    if feedback_type == "custom_solution" and not feedback_data.get("custom_solution_description"):
        raise HTTPException(status_code=400, detail="Custom solution description required")
    
    # Check if feedback already exists for this conflict
    existing_feedback = db.query(SolutionFeedback).filter(
        SolutionFeedback.conflict_id == conflict_id,
        SolutionFeedback.user_id == current_user.id
    ).first()
    
    if existing_feedback:
        # Update existing feedback
        existing_feedback.feedback_type = feedback_type
        existing_feedback.solution_id = solution_id
        existing_feedback.custom_solution_description = feedback_data.get("custom_solution_description")
        existing_feedback.implementation_notes = feedback_data.get("implementation_notes")
        existing_feedback.effectiveness_rating = feedback_data.get("effectiveness_rating")
        existing_feedback.created_at = datetime.utcnow()
        
        db.commit()
        feedback_id = existing_feedback.id
    else:
        # Create new feedback
        feedback = SolutionFeedback(
            conflict_id=conflict_id,
            solution_id=solution_id,
            user_id=current_user.id,
            feedback_type=feedback_type,
            custom_solution_description=feedback_data.get("custom_solution_description"),
            implementation_notes=feedback_data.get("implementation_notes"),
            effectiveness_rating=feedback_data.get("effectiveness_rating")
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        feedback_id = feedback.id
    
    return {
        "message": "Feedback submitted successfully",
        "feedback_id": feedback_id,
        "conflict_id": conflict_id,
        "feedback_type": feedback_type
    }
