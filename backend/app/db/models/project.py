from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Table, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Junction table for Many-to-Many relationship between Conflicts and Elements
conflict_element_association = Table(
    'conflict_elements',
    Base.metadata,
    Column('conflict_id', Integer, ForeignKey('conflicts.id'), primary_key=True),
    Column('element_id', Integer, ForeignKey('elements.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = relationship("Project", back_populates="owner")
    solution_feedback = relationship("SolutionFeedback", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="created")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
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
    elements = relationship("Element", back_populates="ifc_model")

class Element(Base):
    __tablename__ = "elements"
    
    id = Column(Integer, primary_key=True, index=True)
    ifc_model_id = Column(Integer, ForeignKey("ifc_models.id"), nullable=False)
    ifc_id = Column(String(255), nullable=False)  # Original IFC element ID
    element_type = Column(String(100), nullable=False)  # IfcWall, IfcWindow, etc.
    name = Column(String(255))
    description = Column(Text)
    geometry_data = Column(Text)  # JSON string for geometry information
    properties = Column(Text)  # JSON string for element properties
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ifc_model = relationship("IFCModel", back_populates="elements")
    conflicts = relationship("Conflict", secondary=conflict_element_association, back_populates="elements")

class Conflict(Base):
    __tablename__ = "conflicts"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    conflict_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="medium")
    description = Column(Text)
    status = Column(String(50), default="detected")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="conflicts")
    solutions = relationship("Solution", back_populates="conflict")
    elements = relationship("Element", secondary=conflict_element_association, back_populates="conflicts")
    feedback = relationship("SolutionFeedback", back_populates="conflict")

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
    feedback = relationship("SolutionFeedback", back_populates="solution", uselist=False)

class SolutionFeedback(Base):
    __tablename__ = "solution_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False)
    solution_id = Column(Integer, ForeignKey("solutions.id"), nullable=True)  # Null if custom solution
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feedback_type = Column(String(50), nullable=False)  # "selected_suggested", "custom_solution"
    custom_solution_description = Column(Text)  # For custom solutions
    implementation_notes = Column(Text)  # Additional implementation details
    effectiveness_rating = Column(Integer)  # 1-5 rating of solution effectiveness
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conflict = relationship("Conflict")
    solution = relationship("Solution", back_populates="feedback")
    user = relationship("User")