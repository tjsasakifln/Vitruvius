# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request
from sqlalchemy.orm import Session, joinedload
from typing import List
import os
import uuid
from datetime import datetime
from ...db.models.project import Project, IFCModel, Conflict, User, Solution, SolutionFeedback, ProjectCost
from ...db.database import get_db
from ...services.bim_processor import process_ifc_file
from ...tasks.process_ifc import process_ifc_task, convert_ifc_to_gltf, convert_ifc_to_xkt, run_inter_model_clash_detection, invalidate_project_cache, invalidate_model_cache
from ...auth.dependencies import get_current_active_user, require_project_view, require_file_upload, require_project_edit
from ...core.exceptions import (
    ValidationError, ResourceNotFoundError, handle_database_error, 
    handle_file_error, handle_processing_error, FileError, ErrorCode
)
from ...services.rules_engine import suggest_solutions_for_conflict, create_solution_from_rules
from ...services.feedback_service import FeedbackDataCollector
from ...services.ml_service import Predictor
from ...tasks.ml_tasks import train_risk_prediction_model
from ...services.security_logger import security_logger, log_file_upload, log_validation_failure

router = APIRouter(prefix="/projects", tags=["projects"])

# Ensure upload directory exists
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database query optimization helpers
def get_conflicts_with_elements(db: Session, project_id: int):
    """Get conflicts with elements using optimized query to avoid N+1 problems"""
    return db.query(Conflict).options(
        joinedload(Conflict.elements)
    ).filter(Conflict.project_id == project_id).all()

def get_solutions_with_conflict(db: Session, conflict_id: int):
    """Get solutions with conflict data using optimized query"""
    return db.query(Solution).options(
        joinedload(Solution.conflict)
    ).filter(Solution.conflict_id == conflict_id).order_by(Solution.confidence_score.desc()).all()


def ensure_file_exists(file_path: str) -> bool:
    """
    Verify that a file exists and is readable.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file exists and is readable, False otherwise
    """
    try:
        return os.path.exists(file_path) and os.path.isfile(file_path) and os.access(file_path, os.R_OK)
    except Exception:
        return False


def safe_file_cleanup(file_path: str) -> bool:
    """
    Safely remove a file without raising exceptions.
    
    Args:
        file_path: Path to the file to remove
        
    Returns:
        True if file was removed successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Error during file cleanup for {file_path}: {e}")
        return False


def validate_ifc_content(file_content: bytes) -> bool:
    """
    Validate IFC file content for security and format compliance.
    
    Args:
        file_content: Raw file content as bytes
        
    Returns:
        True if file appears to be a valid IFC file, False otherwise
    """
    try:
        # Check for basic IFC header structure
        content_str = file_content.decode('utf-8', errors='ignore')
        
        # IFC files must start with specific header format
        if not content_str.startswith('ISO-10303-21;'):
            return False
        
        # Must contain HEADER section
        if 'HEADER;' not in content_str:
            return False
        
        # Must contain DATA section
        if 'DATA;' not in content_str:
            return False
        
        # Must end with ENDSEC;
        if not content_str.rstrip().endswith('ENDSEC;'):
            return False
        
        # Check for reasonable line count (prevent extremely large files)
        lines = content_str.split('\n')
        if len(lines) > 1000000:  # Max 1M lines
            return False
        
        # Check for suspicious patterns that might indicate malicious content
        suspicious_patterns = [
            'javascript:', 'vbscript:', '<script',
            'eval(', 'exec(', 'import os', 'subprocess',
            '<?php', '<%', '__import__'
        ]
        
        content_lower = content_str.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                return False
        
        # Basic validation of IFC entity structure
        # IFC entities should follow #ID=ENTITY_TYPE(params) format
        import re
        entity_pattern = r'#\d+\s*=\s*[A-Z_]+\([^)]*\);'
        if not re.search(entity_pattern, content_str):
            return False
        
        return True
        
    except Exception as e:
        print(f"Error validating IFC content: {e}")
        return False


@router.get("/", response_model=List[dict])
def get_projects(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all projects for current user"""
    # Use eager loading to avoid N+1 queries if needed in future
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
    current_user: User = Depends(require_file_upload),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Upload IFC model to project"""
    try:
        # Validate input parameters
        if project_id <= 0:
            raise ValidationError("Invalid project ID provided")
        
        if not file or not file.filename:
            raise ValidationError("No file provided")
        
        # Validate file format
        if not file.filename.lower().endswith('.ifc'):
            raise FileError(ErrorCode.INVALID_FILE_TYPE, "File must be IFC format")
        
        # Check file size (limit to 50MB for security)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise FileError(ErrorCode.FILE_TOO_LARGE, "File exceeds maximum size limit of 50MB")
        
        # Validate IFC file content
        if not validate_ifc_content(file_content):
            # Log validation failure with security details
            log_validation_failure(
                validation_type="ifc_file_content",
                user_id=current_user.id,
                input_data=file.filename,
                error="Invalid IFC file format or content",
                request=request
            )
            raise FileError(ErrorCode.INVALID_FILE_TYPE, "Invalid IFC file format or content")
        
        # Reset file pointer for future reads
        await file.seek(0)
        
        # Permission check is handled by require_file_upload dependency
        # But we still need to verify project exists
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ResourceNotFoundError("Project not found")
        except Exception as e:
            raise handle_database_error("project lookup", e)
        
        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(os.path.join(UPLOAD_DIR, "converted"), exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file to disk with error handling
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
        except OSError as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to save file to disk: {str(e)}"
            )
        
        # Verify file was written successfully
        if not ensure_file_exists(file_path):
            raise HTTPException(
                status_code=500, 
                detail="File was not saved successfully"
            )
        
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
        
        # Generate paths for converted files
        file_base = os.path.splitext(unique_filename)[0]
        gltf_path = os.path.join(UPLOAD_DIR, "converted", f"{file_base}.gltf")
        xkt_path = os.path.join(UPLOAD_DIR, "converted", f"{file_base}.xkt")
        
        # Invalidate cache for project when new model is uploaded
        invalidate_project_cache(project_id)
        
        # Start async processing tasks with error handling
        try:
            # Verify file still exists before starting background tasks
            if not ensure_file_exists(file_path):
                raise HTTPException(
                    status_code=500, 
                    detail="File was removed before processing could begin"
                )
            
            task = process_ifc_task.delay(project_id, file_path)
            gltf_task = convert_ifc_to_gltf.delay(file_path, gltf_path, project_id)
            xkt_task = convert_ifc_to_xkt.delay(file_path, xkt_path, project_id)
            
            # Log successful file upload
            log_file_upload(
                user_id=current_user.id,
                filename=file.filename,
                file_size=len(file_content),
                success=True,
                request=request
            )
            
            return {
                "message": "IFC file uploaded successfully",
                "task_id": task.id,
                "gltf_task_id": gltf_task.id,
                "xkt_task_id": xkt_task.id,
                "model_id": ifc_model.id,
                "file_path": file_path
            }
        except Exception as task_err:
            # If background tasks fail, still return success but note the issue
            print(f"Warning: Background task start failed: {task_err}")
            
            # Log successful file upload (even if background processing failed)
            log_file_upload(
                user_id=current_user.id,
                filename=file.filename,
                file_size=len(file_content),
                success=True,
                request=request
            )
            
            return {
                "message": "IFC file uploaded successfully, processing may be delayed",
                "model_id": ifc_model.id,
                "file_path": file_path,
                "warning": "Background processing unavailable"
            }
    
    except (ValidationError, FileError, ResourceNotFoundError) as e:
        # Clean up file if it exists
        if 'file_path' in locals():
            safe_file_cleanup(file_path)
        # Re-raise application exceptions
        raise
    except Exception as e:
        # Clean up file if it exists and return error
        if 'file_path' in locals():
            if safe_file_cleanup(file_path):
                print(f"Cleaned up file after error: {file_path}")
            else:
                print(f"Failed to clean up file: {file_path}")
        
        # Clean up database record if it was created
        if 'ifc_model' in locals():
            try:
                db.delete(ifc_model)
                db.commit()
                print(f"Cleaned up database record for failed upload")
            except Exception as db_cleanup_err:
                print(f"Failed to clean up database record: {db_cleanup_err}")
        
        # Handle as file error
        raise handle_file_error("IFC file upload", e, len(file_content) if 'file_content' in locals() else None)


@router.get("/{project_id}/conflicts")
def get_project_conflicts(
    project_id: int,
    current_user: User = Depends(require_project_view),
    db: Session = Depends(get_db)
):
    """Get conflicts detected in project"""
    try:
        # Validate project_id
        if project_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid project ID")
        
        # Permission check is handled by require_project_view dependency
        # Get real conflicts from database with error handling - using optimized query
        conflicts = get_conflicts_with_elements(db, project_id)
        
        conflict_list = []
        for c in conflicts:
            try:
                # Safely access elements with error handling
                elements = []
                for e in c.elements:
                    try:
                        elements.append({
                            "id": e.id,
                            "ifc_id": e.ifc_id,
                            "type": e.element_type or "Unknown",
                            "name": e.name or "Unnamed"
                        })
                    except Exception as e_err:
                        # Log element error but continue
                        print(f"Error processing element: {e_err}")
                        continue
                
                conflict_list.append({
                    "id": c.id,
                    "type": c.conflict_type or "Unknown",
                    "description": c.description or "No description",
                    "severity": c.severity or "medium",
                    "elements": elements,
                    "status": c.status or "detected",
                    "created_at": c.created_at.isoformat() if c.created_at else None
                })
            except Exception as c_err:
                # Log conflict error but continue
                print(f"Error processing conflict {c.id}: {c_err}")
                continue
        
        return {
            "project_id": project_id,
            "conflicts": conflict_list
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        print(f"Unexpected error in get_project_conflicts: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error while retrieving conflicts"
        )


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
    
    # Get solutions prioritized by confidence score - using optimized query
    solutions = get_solutions_with_conflict(db, conflict_id)
    
    # Also get suggested solutions from similar conflicts in the same project
    similar_solutions = suggest_solutions_for_conflict(conflict_id, project_id, db)
    
    # Filter out duplicates from similar solutions
    existing_solution_ids = {s.id for s in solutions}
    unique_similar_solutions = [s for s in similar_solutions if s["id"] not in existing_solution_ids]
    
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
        ],
        "suggested_solutions": unique_similar_solutions
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
    
    # Update solution confidence score based on feedback
    if solution_id and feedback_type == "selected_suggested":
        solution = db.query(Solution).filter(Solution.id == solution_id).first()
        if solution:
            effectiveness_rating = feedback_data.get("effectiveness_rating", 3)  # Default to neutral
            
            # Adjust confidence based on effectiveness rating (1-5 scale)
            if effectiveness_rating >= 4:  # Good/Excellent
                solution.confidence_score = min(1.0, solution.confidence_score + 0.1)
            elif effectiveness_rating <= 2:  # Poor/Bad
                solution.confidence_score = max(0.1, solution.confidence_score - 0.1)
            # Rating of 3 (neutral) doesn't change confidence
            
            db.commit()
    
    # Collect data for ML training
    feedback_collector = FeedbackDataCollector(db)
    if existing_feedback:
        feedback_collector.collect_feedback_data(existing_feedback)
    else:
        feedback_obj = db.query(SolutionFeedback).filter(SolutionFeedback.id == feedback_id).first()
        if feedback_obj:
            feedback_collector.collect_feedback_data(feedback_obj)
    
    return {
        "message": "Feedback submitted successfully",
        "feedback_id": feedback_id,
        "conflict_id": conflict_id,
        "feedback_type": feedback_type
    }


@router.get("/{project_id}/costs")
def get_project_costs(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get cost parameters for a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    costs = db.query(ProjectCost).filter(ProjectCost.project_id == project_id).all()
    
    return {
        "project_id": project_id,
        "costs": [
            {
                "id": c.id,
                "parameter_name": c.parameter_name,
                "cost": c.cost,
                "created_at": c.created_at,
                "updated_at": c.updated_at
            }
            for c in costs
        ]
    }


@router.post("/{project_id}/costs")
def create_project_cost(
    project_id: int,
    cost_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create or update a cost parameter for a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    parameter_name = cost_data.get("parameter_name")
    cost = cost_data.get("cost")
    
    if not parameter_name or cost is None:
        raise HTTPException(status_code=400, detail="parameter_name and cost are required")
    
    # Check if cost parameter already exists
    existing_cost = db.query(ProjectCost).filter(
        ProjectCost.project_id == project_id,
        ProjectCost.parameter_name == parameter_name
    ).first()
    
    if existing_cost:
        # Update existing cost
        existing_cost.cost = cost
        existing_cost.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_cost)
        return {
            "id": existing_cost.id,
            "parameter_name": existing_cost.parameter_name,
            "cost": existing_cost.cost,
            "updated_at": existing_cost.updated_at
        }
    else:
        # Create new cost parameter
        new_cost = ProjectCost(
            project_id=project_id,
            parameter_name=parameter_name,
            cost=cost
        )
        db.add(new_cost)
        db.commit()
        db.refresh(new_cost)
        return {
            "id": new_cost.id,
            "parameter_name": new_cost.parameter_name,
            "cost": new_cost.cost,
            "created_at": new_cost.created_at
        }


@router.put("/{project_id}/costs/{cost_id}")
def update_project_cost(
    project_id: int,
    cost_id: int,
    cost_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a specific cost parameter"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    cost = db.query(ProjectCost).filter(
        ProjectCost.id == cost_id,
        ProjectCost.project_id == project_id
    ).first()
    if not cost:
        raise HTTPException(status_code=404, detail="Cost parameter not found")
    
    new_cost_value = cost_data.get("cost")
    if new_cost_value is None:
        raise HTTPException(status_code=400, detail="cost is required")
    
    cost.cost = new_cost_value
    cost.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cost)
    
    return {
        "id": cost.id,
        "parameter_name": cost.parameter_name,
        "cost": cost.cost,
        "updated_at": cost.updated_at
    }


@router.delete("/{project_id}/costs/{cost_id}")
def delete_project_cost(
    project_id: int,
    cost_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a cost parameter"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    cost = db.query(ProjectCost).filter(
        ProjectCost.id == cost_id,
        ProjectCost.project_id == project_id
    ).first()
    if not cost:
        raise HTTPException(status_code=404, detail="Cost parameter not found")
    
    db.delete(cost)
    db.commit()
    
    return {"message": "Cost parameter deleted successfully"}


@router.get("/{project_id}/models")
def get_project_models(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all IFC models for a project with their converted file paths"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    models = db.query(IFCModel).filter(IFCModel.project_id == project_id).all()
    
    return {
        "project_id": project_id,
        "models": [
            {
                "id": model.id,
                "filename": model.filename,
                "status": model.status,
                "ifc_path": model.file_path,
                "gltf_path": model.gltf_path,
                "xkt_path": model.xkt_path,
                "processed_at": model.processed_at,
                "created_at": model.created_at
            }
            for model in models
        ]
    }


@router.get("/{project_id}/models/{model_id}/gltf")
def get_model_gltf(
    project_id: int,
    model_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get glTF file URL for a specific model"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    model = db.query(IFCModel).filter(
        IFCModel.id == model_id,
        IFCModel.project_id == project_id
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not model.gltf_path:
        raise HTTPException(status_code=404, detail="glTF file not available")
    
    return {
        "model_id": model_id,
        "gltf_url": f"/static/models/{os.path.basename(model.gltf_path)}",
        "status": model.status
    }


@router.post("/{project_id}/run-inter-model-clash-detection")
def run_inter_model_clash_detection_endpoint(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Run clash detection between multiple IFC models in a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if project has multiple models
    models_count = db.query(IFCModel).filter(IFCModel.project_id == project_id).count()
    if models_count < 2:
        raise HTTPException(status_code=400, detail="Project must have at least 2 IFC models for inter-model clash detection")
    
    # Start the clash detection task
    task = run_inter_model_clash_detection.delay(project_id)
    
    return {
        "message": "Inter-model clash detection started",
        "task_id": task.id,
        "project_id": project_id
    }


@router.get("/{project_id}/predict-risk")
def predict_project_risk(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered risk prediction for a project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Use ML predictor to get risk assessment
    predictor = Predictor()
    risk_prediction = predictor.predict_project_risk(project_id)
    
    if "error" in risk_prediction:
        raise HTTPException(status_code=500, detail=risk_prediction["error"])
    
    return risk_prediction


@router.post("/ml/train-model")
def trigger_model_training(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Trigger ML model training (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only administrators can trigger model training")
    
    # Start async model training task
    task = train_risk_prediction_model.delay()
    
    return {
        "message": "ML model training started",
        "task_id": task.id
    }


@router.get("/ml/model-status")
def get_model_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get status of ML models"""
    import os
    
    model_path = "/app/models"
    risk_model_file = "risk_prediction_model.pkl"
    encoders_file = "label_encoders.pkl"
    scaler_file = "feature_scaler.pkl"
    
    model_exists = os.path.exists(os.path.join(model_path, risk_model_file))
    encoders_exist = os.path.exists(os.path.join(model_path, encoders_file))
    scaler_exists = os.path.exists(os.path.join(model_path, scaler_file))
    
    models_ready = model_exists and encoders_exist and scaler_exists
    
    # Get training data count
    from ..db.models.analytics import HistoricalConflict
    training_data_count = db.query(HistoricalConflict).count()
    
    return {
        "models_ready": models_ready,
        "model_exists": model_exists,
        "encoders_exist": encoders_exist,
        "scaler_exists": scaler_exists,
        "training_data_count": training_data_count,
        "minimum_data_required": 10
    }