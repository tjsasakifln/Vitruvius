# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

"""
Database initialization script.
Creates all tables and indexes without requiring Alembic migrations.
"""

from sqlalchemy import create_engine, text
from .database import Base, SessionLocal, SQLALCHEMY_DATABASE_URL
from .models import project, collaboration
import logging

logger = logging.getLogger(__name__)

def create_database_tables():
    """Create all database tables"""
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Database tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        return False

def create_indexes():
    """Create additional indexes for performance"""
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        
        with engine.connect() as conn:
            # Create comprehensive indexes for performance optimization
            indexes = [
                # Primary foreign key indexes
                "CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects (owner_id);",
                "CREATE INDEX IF NOT EXISTS idx_ifc_models_project_id ON ifc_models (project_id);",
                "CREATE INDEX IF NOT EXISTS idx_elements_ifc_model_id ON elements (ifc_model_id);",
                "CREATE INDEX IF NOT EXISTS idx_conflicts_project_id ON conflicts (project_id);",
                "CREATE INDEX IF NOT EXISTS idx_solutions_conflict_id ON solutions (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_project_costs_project_id ON project_costs (project_id);",
                "CREATE INDEX IF NOT EXISTS idx_solution_feedback_conflict_id ON solution_feedback (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_solution_feedback_solution_id ON solution_feedback (solution_id);",
                "CREATE INDEX IF NOT EXISTS idx_solution_feedback_user_id ON solution_feedback (user_id);",
                
                # Collaboration foreign key indexes
                "CREATE INDEX IF NOT EXISTS idx_comments_conflict_id ON comments (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments (user_id);",
                "CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments (parent_comment_id);",
                "CREATE INDEX IF NOT EXISTS idx_comment_attachments_comment_id ON comment_attachments (comment_id);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_conflict_id ON annotations (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_element_id ON annotations (element_id);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_user_id ON annotations (user_id);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_resolved_by_id ON annotations (resolved_by_id);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_project_id ON activity_logs (project_id);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_conflict_id ON activity_logs (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs (user_id);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_assignments_conflict_id ON conflict_assignments (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_assignments_assigned_to_id ON conflict_assignments (assigned_to_id);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_assignments_assigned_by_id ON conflict_assignments (assigned_by_id);",
                "CREATE INDEX IF NOT EXISTS idx_workflow_states_conflict_id ON workflow_states (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_workflow_states_changed_by_id ON workflow_states (changed_by_id);",
                "CREATE INDEX IF NOT EXISTS idx_workflow_states_approved_by_id ON workflow_states (approved_by_id);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications (user_id);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_project_id ON notifications (project_id);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_conflict_id ON notifications (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_watches_conflict_id ON conflict_watches (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_watches_user_id ON conflict_watches (user_id);",
                
                # Frequently queried columns
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);",
                "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active);",
                "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status);",
                "CREATE INDEX IF NOT EXISTS idx_projects_sync_status ON projects (sync_status);",
                "CREATE INDEX IF NOT EXISTS idx_ifc_models_status ON ifc_models (status);",
                "CREATE INDEX IF NOT EXISTS idx_elements_ifc_id ON elements (ifc_id);",
                "CREATE INDEX IF NOT EXISTS idx_elements_element_type ON elements (element_type);",
                "CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts (status);",
                "CREATE INDEX IF NOT EXISTS idx_conflicts_severity ON conflicts (severity);",
                "CREATE INDEX IF NOT EXISTS idx_conflicts_type ON conflicts (conflict_type);",
                "CREATE INDEX IF NOT EXISTS idx_solutions_status ON solutions (status);",
                "CREATE INDEX IF NOT EXISTS idx_solutions_solution_type ON solutions (solution_type);",
                "CREATE INDEX IF NOT EXISTS idx_comments_type ON comments (comment_type);",
                "CREATE INDEX IF NOT EXISTS idx_comments_is_internal ON comments (is_internal);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations (annotation_type);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_is_resolved ON annotations (is_resolved);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_priority ON annotations (priority);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_activity_type ON activity_logs (activity_type);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_entity_type ON activity_logs (entity_type);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_assignments_status ON conflict_assignments (status);",
                "CREATE INDEX IF NOT EXISTS idx_workflow_states_state ON workflow_states (state);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications (notification_type);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications (is_read);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_priority ON notifications (priority);",
                
                # Timestamp indexes for time-based queries
                "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_projects_last_sync_at ON projects (last_sync_at);",
                "CREATE INDEX IF NOT EXISTS idx_ifc_models_created_at ON ifc_models (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_ifc_models_processed_at ON ifc_models (processed_at);",
                "CREATE INDEX IF NOT EXISTS idx_conflicts_created_at ON conflicts (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_solutions_created_at ON solutions (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_created_at ON annotations (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_resolved_at ON annotations (resolved_at);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_assignments_due_date ON conflict_assignments (due_date);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_assignments_completed_at ON conflict_assignments (completed_at);",
                "CREATE INDEX IF NOT EXISTS idx_workflow_states_created_at ON workflow_states (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_read_at ON notifications (read_at);",
                
                # Composite indexes for common query patterns
                "CREATE INDEX IF NOT EXISTS idx_conflicts_project_status ON conflicts (project_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_conflicts_project_severity ON conflicts (project_id, severity);",
                "CREATE INDEX IF NOT EXISTS idx_conflicts_project_type ON conflicts (project_id, conflict_type);",
                "CREATE INDEX IF NOT EXISTS idx_solutions_conflict_confidence ON solutions (conflict_id, confidence_score DESC);",
                "CREATE INDEX IF NOT EXISTS idx_solutions_conflict_status ON solutions (conflict_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_comments_conflict_created ON comments (conflict_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_comments_user_created ON comments (user_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_conflict_resolved ON annotations (conflict_id, is_resolved);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_project_created ON activity_logs (project_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_user_created ON activity_logs (user_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications (user_id, is_read);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications (user_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_project_costs_project_param ON project_costs (project_id, parameter_name);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_assignments_user_status ON conflict_assignments (assigned_to_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_workflow_states_conflict_created ON workflow_states (conflict_id, created_at DESC);",
                
                # Performance optimization indexes
                "CREATE INDEX IF NOT EXISTS idx_elements_ifc_model_type ON elements (ifc_model_id, element_type);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_elements_conflict ON conflict_elements (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_conflict_elements_element ON conflict_elements (element_id);",
                "CREATE INDEX IF NOT EXISTS idx_users_active_created ON users (is_active, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_projects_owner_status ON projects (owner_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_ifc_models_project_status ON ifc_models (project_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_solutions_confidence_created ON solutions (confidence_score DESC, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_entity_created ON activity_logs (entity_type, entity_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_type_created ON notifications (notification_type, created_at DESC);"
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    logger.debug(f"Created index: {index_sql.split()[5]}")
                except Exception as e:
                    logger.warning(f"Index creation warning for {index_sql}: {e}")
        
        logger.info("✅ Database indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        return False

def init_database():
    """Initialize the complete database"""
    logger.info("🚀 Initializing database...")
    
    success = True
    success &= create_database_tables()
    success &= create_indexes()
    
    if success:
        logger.info("✅ Database initialization completed successfully")
    else:
        logger.error("❌ Database initialization failed")
    
    return success

if __name__ == "__main__":
    init_database()