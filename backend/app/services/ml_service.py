# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..db.models.analytics import HistoricalConflict
from ..db.models.project import Project, Conflict

class ModelTrainer:
    """Service for training ML models to predict conflict risk"""
    
    def __init__(self):
        self.model_path = "/app/models"
        self.risk_model_file = "risk_prediction_model.pkl"
        self.encoders_file = "label_encoders.pkl"
        self.scaler_file = "feature_scaler.pkl"
        
        # Ensure model directory exists
        os.makedirs(self.model_path, exist_ok=True)
    
    def get_training_data(self) -> pd.DataFrame:
        """Load historical conflict data from database"""
        with SessionLocal() as db:
            # Query all historical conflicts
            conflicts = db.query(HistoricalConflict).all()
            
            if not conflicts:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for conflict in conflicts:
                data.append({
                    'element_category_1': conflict.element_category_1,
                    'element_category_2': conflict.element_category_2,
                    'discipline_1': conflict.discipline_1,
                    'discipline_2': conflict.discipline_2,
                    'conflict_type': conflict.conflict_type,
                    'severity': conflict.severity,
                    'resolution_cost': conflict.resolution_cost or 0,
                    'resolution_time_days': conflict.resolution_time_days or 0,
                    'solution_feedback_positive': conflict.solution_feedback_positive,
                    'effectiveness_rating': conflict.effectiveness_rating or 3
                })
            
            return pd.DataFrame(data)
    
    def preprocess_data(self, df: pd.DataFrame) -> tuple:
        """Preprocess data for training"""
        if df.empty:
            return None, None, None, None
        
        # Prepare features
        categorical_features = ['element_category_1', 'element_category_2', 
                              'discipline_1', 'discipline_2', 'conflict_type', 'severity']
        numerical_features = ['resolution_cost', 'resolution_time_days', 'effectiveness_rating']
        
        # Initialize encoders
        encoders = {}
        for feature in categorical_features:
            encoder = LabelEncoder()
            df[f'{feature}_encoded'] = encoder.fit_transform(df[feature])
            encoders[feature] = encoder
        
        # Prepare feature matrix
        feature_columns = [f'{f}_encoded' for f in categorical_features] + numerical_features
        X = df[feature_columns].copy()
        
        # Handle missing values
        X.fillna(0, inplace=True)
        
        # Scale numerical features
        scaler = StandardScaler()
        X[numerical_features] = scaler.fit_transform(X[numerical_features])
        
        # Target variable (predict positive feedback)
        y = df['solution_feedback_positive'].astype(int)
        
        return X, y, encoders, scaler
    
    def train_and_save_model(self) -> Dict[str, Any]:
        """Train the risk prediction model and save it"""
        # Get training data
        df = self.get_training_data()
        
        if df.empty:
            return {"error": "No training data available"}
        
        if len(df) < 10:
            return {"error": f"Insufficient training data. Need at least 10 samples, got {len(df)}"}
        
        # Preprocess data
        X, y, encoders, scaler = self.preprocess_data(df)
        
        if X is None:
            return {"error": "Data preprocessing failed"}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Save model and preprocessing components
        model_file_path = os.path.join(self.model_path, self.risk_model_file)
        encoders_file_path = os.path.join(self.model_path, self.encoders_file)
        scaler_file_path = os.path.join(self.model_path, self.scaler_file)
        
        joblib.dump(model, model_file_path)
        joblib.dump(encoders, encoders_file_path)
        joblib.dump(scaler, scaler_file_path)
        
        return {
            "success": True,
            "training_samples": len(df),
            "test_accuracy": accuracy,
            "model_saved": model_file_path,
            "feature_importance": dict(zip(X.columns, model.feature_importances_))
        }

class Predictor:
    """Service for making risk predictions using trained models"""
    
    def __init__(self):
        self.model_path = "/app/models"
        self.risk_model_file = "risk_prediction_model.pkl"
        self.encoders_file = "label_encoders.pkl"
        self.scaler_file = "feature_scaler.pkl"
        
        self.model = None
        self.encoders = None
        self.scaler = None
        self._load_models()
    
    def _load_models(self):
        """Load trained models and preprocessing components"""
        try:
            model_file_path = os.path.join(self.model_path, self.risk_model_file)
            encoders_file_path = os.path.join(self.model_path, self.encoders_file)
            scaler_file_path = os.path.join(self.model_path, self.scaler_file)
            
            if all(os.path.exists(f) for f in [model_file_path, encoders_file_path, scaler_file_path]):
                self.model = joblib.load(model_file_path)
                self.encoders = joblib.load(encoders_file_path)
                self.scaler = joblib.load(scaler_file_path)
            
        except Exception as e:
            print(f"Error loading models: {e}")
            self.model = None
            self.encoders = None
            self.scaler = None
    
    def predict_project_risk(self, project_id: int) -> Dict[str, Any]:
        """Predict risk score for a project based on its conflicts"""
        if not self.model or not self.encoders or not self.scaler:
            return {"error": "ML models not available. Please train the model first."}
        
        with SessionLocal() as db:
            # Get project conflicts
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"error": "Project not found"}
            
            conflicts = db.query(Conflict).filter(Conflict.project_id == project_id).all()
            if not conflicts:
                return {"risk_score": 0.0, "message": "No conflicts detected"}
            
            risk_scores = []
            conflict_predictions = []
            
            for conflict in conflicts:
                if len(conflict.elements) >= 2:
                    element_1 = conflict.elements[0]
                    element_2 = conflict.elements[1]
                    
                    # Prepare features for prediction
                    features = {
                        'element_category_1': element_1.element_type,
                        'element_category_2': element_2.element_type,
                        'discipline_1': self._extract_discipline(element_1.element_type),
                        'discipline_2': self._extract_discipline(element_2.element_type),
                        'conflict_type': conflict.conflict_type,
                        'severity': conflict.severity,
                        'resolution_cost': 0,  # Unknown for new conflicts
                        'resolution_time_days': 0,  # Unknown for new conflicts
                        'effectiveness_rating': 3  # Neutral default
                    }
                    
                    risk_score = self._predict_single_conflict(features)
                    risk_scores.append(risk_score)
                    
                    conflict_predictions.append({
                        'conflict_id': conflict.id,
                        'risk_score': risk_score,
                        'description': conflict.description
                    })
            
            # Calculate overall project risk
            if risk_scores:
                overall_risk = np.mean(risk_scores)
                risk_level = self._get_risk_level(overall_risk)
            else:
                overall_risk = 0.0
                risk_level = "Low"
            
            return {
                "project_id": project_id,
                "overall_risk_score": float(overall_risk),
                "risk_level": risk_level,
                "total_conflicts": len(conflicts),
                "analyzed_conflicts": len(risk_scores),
                "conflict_predictions": conflict_predictions
            }
    
    def _predict_single_conflict(self, features: Dict[str, Any]) -> float:
        """Predict risk for a single conflict"""
        try:
            # Create DataFrame from features
            df = pd.DataFrame([features])
            
            # Encode categorical features
            categorical_features = ['element_category_1', 'element_category_2', 
                                  'discipline_1', 'discipline_2', 'conflict_type', 'severity']
            
            for feature in categorical_features:
                if feature in self.encoders:
                    encoder = self.encoders[feature]
                    try:
                        df[f'{feature}_encoded'] = encoder.transform(df[feature])
                    except ValueError:
                        # Unknown category, use most frequent class
                        df[f'{feature}_encoded'] = 0
                else:
                    df[f'{feature}_encoded'] = 0
            
            # Prepare feature matrix
            numerical_features = ['resolution_cost', 'resolution_time_days', 'effectiveness_rating']
            feature_columns = [f'{f}_encoded' for f in categorical_features] + numerical_features
            
            X = df[feature_columns].copy()
            X.fillna(0, inplace=True)
            
            # Scale numerical features
            X[numerical_features] = self.scaler.transform(X[numerical_features])
            
            # Get prediction probability
            risk_prob = self.model.predict_proba(X)[0][1]  # Probability of positive outcome
            
            # Convert to risk score (inverse of positive outcome probability)
            risk_score = 1.0 - risk_prob
            
            return float(risk_score)
        
        except Exception as e:
            print(f"Error in prediction: {e}")
            return 0.5  # Return neutral risk if prediction fails
    
    def _extract_discipline(self, element_type: str) -> str:
        """Extract discipline from element type"""
        element_type_lower = element_type.lower()
        
        if any(x in element_type_lower for x in ['wall', 'slab', 'column', 'beam', 'foundation']):
            return "Structural"
        elif any(x in element_type_lower for x in ['door', 'window', 'furniture', 'space']):
            return "Architectural"
        elif any(x in element_type_lower for x in ['pipe', 'duct', 'equipment', 'fitting']):
            return "MEP"
        elif any(x in element_type_lower for x in ['railing', 'stair', 'ramp']):
            return "Circulation"
        else:
            return "Other"
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 0.7:
            return "High"
        elif risk_score >= 0.4:
            return "Medium"
        else:
            return "Low"