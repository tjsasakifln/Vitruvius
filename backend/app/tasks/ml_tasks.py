# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from celery import Celery
from ..core.config import settings
from ..services.ml_service import ModelTrainer

# Configure Celery
celery_app = Celery('ml_tasks', broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

@celery_app.task
def train_risk_prediction_model():
    """
    Celery task to train the risk prediction ML model
    """
    try:
        print("Starting ML model training task...")
        
        trainer = ModelTrainer()
        result = trainer.train_and_save_model()
        
        if result.get("success"):
            print(f"Model training completed successfully. Accuracy: {result.get('test_accuracy', 'N/A')}")
        else:
            print(f"Model training failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error in ML training task: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

@celery_app.task
def retrain_model_with_new_data():
    """
    Celery task to retrain model when new feedback data is available
    """
    try:
        print("Starting model retraining with new data...")
        
        trainer = ModelTrainer()
        result = trainer.train_and_save_model()
        
        if result.get("success"):
            print(f"Model retraining completed. New accuracy: {result.get('test_accuracy', 'N/A')}")
        else:
            print(f"Model retraining failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error in ML retraining task: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "error": error_msg
        }