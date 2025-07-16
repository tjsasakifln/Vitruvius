from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="created")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ifc_models = relationship("IFCModel", back_populates="project")
    conflicts = relationship("Conflict", back_populates="project")

class IFCModel(Base):
    __tablename__ = "ifc_models"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    status = Column(String(50), default="uploaded")
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="ifc_models")

class Conflict(Base):
    __tablename__ = "conflicts"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    conflict_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="medium")
    description = Column(Text)
    elements_involved = Column(Text)  # JSON string
    status = Column(String(50), default="detected")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="conflicts")
    solutions = relationship("Solution", back_populates="conflict")

class Solution(Base):
    __tablename__ = "solutions"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False)
    solution_type = Column(String(100), nullable=False)
    description = Column(Text)
    estimated_cost = Column(Integer)  # in cents
    estimated_time = Column(Integer)  # in days
    confidence_score = Column(Integer)  # 0-100
    status = Column(String(50), default="proposed")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conflict = relationship("Conflict", back_populates="solutions")