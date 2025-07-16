from celery import Celery
# from ..services.bim_processor import process_ifc_file
# from ..services.ia_prescriptive import run_prescriptive_analysis

# Configure Celery
celery_app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

@celery_app.task
def process_ifc_task(file_path: str):
    """
    Celery task to process an IFC file asynchronously.
    """
    print(f"Starting IFC processing for: {file_path}")
    # bim_data = process_ifc_file(file_path)
    # analysis_results = run_prescriptive_analysis(bim_data)
    # print(f"Analysis complete for: {file_path}")
    # return analysis_results
    return {"status": "completed", "file": file_path}
