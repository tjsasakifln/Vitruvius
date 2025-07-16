from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from ...db.models.project import Project
from ...db.database import get_db
from ...services.bim_processor import process_ifc_file
from ...tasks.process_ifc import process_ifc_task

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", response_model=List[dict])
def get_projects(db: Session = Depends(get_db)):
    """Get all projects"""
    projects = db.query(Project).all()
    return [{"id": p.id, "name": p.name, "status": p.status} for p in projects]

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
    
    # Save file and start processing
    file_content = await file.read()
    
    # Start async processing
    task = process_ifc_task.delay(project_id, file_content)
    
    return {"message": "IFC file uploaded", "task_id": task.id}

@router.get("/{project_id}/conflicts")
def get_project_conflicts(project_id: int, db: Session = Depends(get_db)):
    """Get conflicts detected in project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Return mock conflicts for now
    return {
        "conflicts": [
            {
                "id": 1,
                "type": "collision",
                "description": "Beam conflicts with column",
                "severity": "high",
                "elements": ["beam_123", "column_456"]
            }
        ]
    }