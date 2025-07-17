# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Table, Boolean, Float, Index
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
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="created", index=True)
    aps_project_id = Column(String(255))  # APS project ID for integration
    aps_hub_id = Column(String(255))      # APS hub ID for integration
    
    # Planning Tool Integration Fields
    planning_tool_connected = Column(String(50))  # 'primavera', 'msproject', 'smartsheet', etc.
    planning_tool_api_key = Column(String(500))  # Encrypted API key for planning tool
    planning_tool_project_id = Column(String(255))  # Project ID in external planning tool
    planning_tool_base_url = Column(String(500))  # Base URL for planning tool API
    planning_tool_config = Column(Text)  # JSON string for additional configuration
    
    # Budget Tool Integration Fields  
    budget_tool_connected = Column(String(50))  # 'sage', 'quickbooks', 'oracle_cost', etc.
    budget_tool_api_key = Column(String(500))  # Encrypted API key for budget tool
    budget_tool_project_id = Column(String(255))  # Project ID in external budget tool
    budget_tool_base_url = Column(String(500))  # Base URL for budget tool API
    budget_tool_config = Column(Text)  # JSON string for additional configuration
    
    # Integration Status
    last_sync_at = Column(DateTime)  # Last successful synchronization
    sync_status = Column(String(50), default="not_configured")  # 'not_configured', 'connected', 'syncing', 'error'
    sync_error_message = Column(Text)  # Last sync error message
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    ifc_models = relationship("IFCModel", back_populates="project")
    conflicts = relationship("Conflict", back_populates="project")
    costs = relationship("ProjectCost", back_populates="project")

class ProjectCost(Base):
    __tablename__ = "project_costs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    parameter_name = Column(String(100), index=True, nullable=False)  # Ex: "CONCRETE_M3", "STEEL_KG", "LABOR_HOUR"
    cost = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="costs")

class IFCModel(Base):
    __tablename__ = "ifc_models"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    gltf_path = Column(String(500))  # Path to converted glTF file
    xkt_path = Column(String(500))   # Path to converted XKT file
    status = Column(String(50), default="uploaded", index=True)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="ifc_models")
    elements = relationship("Element", back_populates="ifc_model")

class Element(Base):
    __tablename__ = "elements"
    
    id = Column(Integer, primary_key=True, index=True)
    ifc_model_id = Column(Integer, ForeignKey("ifc_models.id"), nullable=False, index=True)
    ifc_id = Column(String(255), nullable=False, index=True)  # Original IFC element ID
    element_type = Column(String(100), nullable=False, index=True)  # IfcWall, IfcWindow, etc.
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
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    conflict_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), default="medium", index=True)
    description = Column(Text)
    status = Column(String(50), default="detected", index=True)
    aps_issue_id = Column(String(255))  # APS issue ID for integration
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="conflicts")
    solutions = relationship("Solution", back_populates="conflict")
    elements = relationship("Element", secondary=conflict_element_association, back_populates="conflicts")
    feedback = relationship("SolutionFeedback", back_populates="conflict")

class Solution(Base):
    __tablename__ = "solutions"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False, index=True)
    solution_type = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    estimated_cost = Column(Integer)  # in cents
    estimated_time = Column(Integer)  # in days
    confidence_score = Column(Float, default=1.0, nullable=False, index=True)  # 0.0-1.0
    status = Column(String(50), default="proposed", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conflict = relationship("Conflict", back_populates="solutions")
    feedback = relationship("SolutionFeedback", back_populates="solution", uselist=False)

class SolutionFeedback(Base):
    __tablename__ = "solution_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"), nullable=False, index=True)
    solution_id = Column(Integer, ForeignKey("solutions.id"), nullable=True, index=True)  # Null if custom solution
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    feedback_type = Column(String(50), nullable=False)  # "selected_suggested", "custom_solution"
    custom_solution_description = Column(Text)  # For custom solutions
    implementation_notes = Column(Text)  # Additional implementation details
    effectiveness_rating = Column(Integer)  # 1-5 rating of solution effectiveness
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conflict = relationship("Conflict")
    solution = relationship("Solution", back_populates="feedback")
    user = relationship("User")