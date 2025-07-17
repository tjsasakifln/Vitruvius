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
            # Create additional indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_conflicts_project_status ON conflicts (project_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_elements_ifc_model ON elements (ifc_model_id);",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_comments_conflict ON comments (conflict_id);",
                "CREATE INDEX IF NOT EXISTS idx_annotations_conflict ON annotations (conflict_id);"
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
        
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