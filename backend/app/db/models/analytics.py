# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class HistoricalConflict(Base):
    __tablename__ = "historical_conflicts"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    element_category_1 = Column(String(100), nullable=False)
    element_category_2 = Column(String(100), nullable=False)
    discipline_1 = Column(String(100), nullable=False)
    discipline_2 = Column(String(100), nullable=False)
    conflict_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    resolution_cost = Column(Float)  # Cost in currency units
    resolution_time_days = Column(Integer)  # Time in days
    solution_feedback_positive = Column(Boolean, nullable=False)  # True if positive feedback
    effectiveness_rating = Column(Integer)  # 1-5 rating from feedback
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project")