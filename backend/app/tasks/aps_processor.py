# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import os
import time
import tempfile
import logging
from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from ..services.aps_integration import APSIntegration
from ..db.models.project import Project, IFCModel
from ..db.database import DATABASE_URL
from ..core.config import settings
from .process_ifc import process_ifc_task

logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery('aps_tasks', broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

# Database setup for Celery tasks
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# APS Configuration
APS_CLIENT_ID = os.getenv("APS_CLIENT_ID", "")
APS_CLIENT_SECRET = os.getenv("APS_CLIENT_SECRET", "")
APS_CALLBACK_URL = os.getenv("APS_CALLBACK_URL", "http://localhost:8000/api/v1/aps/callback")

@celery_app.task
def process_aps_model_task(urn: str, project_id: int, model_id: int, access_token: str):
    """
    Process an APS model by translating it to IFC and running clash detection
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Starting APS model processing for model {model_id}, URN: {urn}")
        
        # Get the IFC model record
        ifc_model = db.query(IFCModel).filter(IFCModel.id == model_id).first()
        if not ifc_model:
            return {"status": "failed", "error": "IFC model not found"}
        
        # Initialize APS integration
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        aps.set_token(access_token)
        
        # Step 1: Start IFC translation
        logger.info("Starting IFC translation...")
        translation_job = aps.translate_to_ifc(urn, force_translate=True)
        
        # Step 2: Monitor translation progress
        logger.info("Monitoring translation progress...")
        max_attempts = 60  # 5 minutes with 5-second intervals
        attempt = 0
        
        while attempt < max_attempts:
            try:
                manifest = aps.get_derivative_manifest(urn)
                status = manifest.get("status", "")
                
                if status == "success":
                    logger.info("Translation completed successfully")
                    break
                elif status == "failed":
                    error_msg = manifest.get("messages", [{}])[0].get("message", "Unknown error")
                    logger.error(f"Translation failed: {error_msg}")
                    ifc_model.status = "translation_failed"
                    db.commit()
                    return {"status": "failed", "error": f"Translation failed: {error_msg}"}
                elif status == "inprogress":
                    logger.info(f"Translation in progress... (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(5)  # Wait 5 seconds before checking again
                    attempt += 1
                else:
                    logger.info(f"Translation status: {status}")
                    time.sleep(5)
                    attempt += 1
                    
            except Exception as e:
                logger.error(f"Error checking translation status: {str(e)}")
                time.sleep(5)
                attempt += 1
        
        if attempt >= max_attempts:
            logger.error("Translation timed out")
            ifc_model.status = "translation_timeout"
            db.commit()
            return {"status": "failed", "error": "Translation timed out"}
        
        # Step 3: Find and download IFC derivative
        logger.info("Downloading IFC derivative...")
        manifest = aps.get_derivative_manifest(urn)
        
        ifc_derivative = None
        for derivative in manifest.get("derivatives", []):
            if derivative.get("outputType") == "ifc":
                for child in derivative.get("children", []):
                    if child.get("role") == "ifc":
                        ifc_derivative = child
                        break
                if ifc_derivative:
                    break
        
        if not ifc_derivative:
            logger.error("IFC derivative not found in manifest")
            ifc_model.status = "ifc_not_found"
            db.commit()
            return {"status": "failed", "error": "IFC derivative not found"}
        
        # Download the IFC file
        derivative_urn = ifc_derivative.get("urn", "")
        if not derivative_urn:
            logger.error("IFC derivative URN not found")
            ifc_model.status = "ifc_urn_not_found"
            db.commit()
            return {"status": "failed", "error": "IFC derivative URN not found"}
        
        ifc_content = aps.download_derivative(urn, derivative_urn)
        
        # Step 4: Save IFC file to disk
        logger.info("Saving IFC file to disk...")
        temp_dir = tempfile.gettempdir()
        ifc_filename = f"aps_model_{model_id}_{int(time.time())}.ifc"
        ifc_path = os.path.join(temp_dir, ifc_filename)
        
        with open(ifc_path, 'wb') as f:
            f.write(ifc_content)
        
        # Update model record with file path
        ifc_model.file_path = ifc_path
        ifc_model.status = "downloaded"
        db.commit()
        
        logger.info(f"IFC file saved to: {ifc_path}")
        
        # Step 5: Start Vitruvius processing
        logger.info("Starting Vitruvius processing...")
        processing_task = process_ifc_task.delay(project_id, ifc_path)
        
        # Update model status
        ifc_model.status = "processing"
        db.commit()
        
        logger.info(f"APS model processing completed for model {model_id}")
        
        return {
            "status": "completed",
            "model_id": model_id,
            "project_id": project_id,
            "ifc_path": ifc_path,
            "processing_task_id": processing_task.id
        }
        
    except Exception as e:
        logger.error(f"Error processing APS model: {str(e)}")
        
        # Update model status
        if 'ifc_model' in locals() and ifc_model:
            ifc_model.status = "failed"
            db.commit()
        
        return {
            "status": "failed",
            "error": str(e),
            "model_id": model_id
        }
    
    finally:
        db.close()

@celery_app.task
def sync_aps_issues_task(project_id: int, aps_project_id: str, access_token: str):
    """
    Sync issues between Vitruvius and APS
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Starting APS issues sync for project {project_id}")
        
        # Initialize APS integration
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        aps.set_token(access_token)
        
        # Get issues from APS
        aps_issues = aps.get_issues(aps_project_id)
        
        # Process each issue
        for issue in aps_issues:
            issue_id = issue["id"]
            title = issue["attributes"]["title"]
            description = issue["attributes"]["description"]
            
            # Check if this is a Vitruvius-created issue
            if "Vitruvius" in title or "Vitruvius" in description:
                # Find corresponding conflict
                custom_attrs = issue["attributes"].get("customAttributes", [])
                vitruvius_conflict_id = None
                
                for attr in custom_attrs:
                    if attr.get("name") == "Vitruvius Conflict ID":
                        vitruvius_conflict_id = attr.get("value")
                        break
                
                if vitruvius_conflict_id:
                    # Update conflict with APS issue status
                    from ..db.models.project import Conflict
                    conflict = db.query(Conflict).filter(
                        Conflict.id == int(vitruvius_conflict_id),
                        Conflict.project_id == project_id
                    ).first()
                    
                    if conflict:
                        # Update conflict status based on APS issue status
                        aps_status = issue["attributes"]["status"]
                        if aps_status == "closed":
                            conflict.status = "resolved"
                        elif aps_status == "open":
                            conflict.status = "reported"
                        
                        db.commit()
                        logger.info(f"Updated conflict {vitruvius_conflict_id} status to {conflict.status}")
        
        logger.info(f"APS issues sync completed for project {project_id}")
        
        return {
            "status": "completed",
            "project_id": project_id,
            "issues_processed": len(aps_issues)
        }
        
    except Exception as e:
        logger.error(f"Error syncing APS issues: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "project_id": project_id
        }
    
    finally:
        db.close()

@celery_app.task
def create_aps_issue_task(conflict_id: int, aps_project_id: str, access_token: str, issue_data: dict):
    """
    Create an APS issue for a Vitruvius conflict
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Creating APS issue for conflict {conflict_id}")
        
        # Get the conflict
        from ..db.models.project import Conflict
        conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
        
        if not conflict:
            return {"status": "failed", "error": "Conflict not found"}
        
        # Initialize APS integration
        aps = APSIntegration(APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL)
        aps.set_token(access_token)
        
        # Prepare issue data
        aps_issue_data = {
            "title": f"Clash: {conflict.conflict_type} - {conflict.description}",
            "description": f"Conflict detected by Vitruvius AI:

{conflict.description}

Severity: {conflict.severity}
Status: {conflict.status}",
            "priority": "high" if conflict.severity == "high" else "normal",
            "custom_attributes": [
                {
                    "name": "Vitruvius Conflict ID",
                    "value": str(conflict.id)
                },
                {
                    "name": "Conflict Type",
                    "value": conflict.conflict_type
                },
                {
                    "name": "Detection Method",
                    "value": "Vitruvius AI"
                }
            ]
        }
        
        # Merge with provided issue data
        aps_issue_data.update(issue_data)
        
        # Create the issue
        issue = aps.create_issue(aps_project_id, aps_issue_data)
        
        # Update conflict with APS issue ID
        conflict.aps_issue_id = issue["data"]["id"]
        db.commit()
        
        logger.info(f"Created APS issue {issue['data']['id']} for conflict {conflict_id}")
        
        return {
            "status": "completed",
            "conflict_id": conflict_id,
            "issue_id": issue["data"]["id"]
        }
        
    except Exception as e:
        logger.error(f"Error creating APS issue: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "conflict_id": conflict_id
        }
    
    finally:
        db.close()
