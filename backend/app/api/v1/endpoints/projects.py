from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from datetime import datetime
from ...db.models.project import Project, IFCModel, Conflict
from ...db.database import get_db
from ...services.bim_processor import process_ifc_file
from ...tasks.process_ifc import process_ifc_task

router = APIRouter(prefix="/projects", tags=["projects"])

# Ensure upload directory exists
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/", response_model=List[dict])
def get_projects(db: Session = Depends(get_db)):
    """Get all projects"""
    projects = db.query(Project).all()
    return [{"id": p.id, "name": p.name, "status": p.status, "created_at": p.created_at} for p in projects]

@router.post("/", response_model=dict)
def create_project(project_data: dict, db: Session = Depends(get_db)):
    """Create a new project"""
    project = Project(
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
    db: Session = Depends(get_db)
):
    """Upload IFC model to project"""
    if not file.filename.endswith('.ifc'):
        raise HTTPException(status_code=400, detail="File must be IFC format")
    
    project = db.query(Project).filter(Project.id == project_id).first()
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
def get_project_conflicts(project_id: int, db: Session = Depends(get_db)):
    """Get conflicts detected in project"""
    project = db.query(Project).filter(Project.id == project_id).first()
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
                "elements": c.elements_involved.split(",") if c.elements_involved else [],
                "status": c.status,
                "created_at": c.created_at
            }
            for c in conflicts
        ]
    }