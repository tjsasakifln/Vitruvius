"""
Migration script to add SolutionFeedback table
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/vitruvius_db")

def run_migration():
    """Run the migration to add solution_feedback table"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.begin() as conn:
            # Create solution_feedback table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS solution_feedback (
                    id SERIAL PRIMARY KEY,
                    conflict_id INTEGER NOT NULL REFERENCES conflicts(id),
                    solution_id INTEGER REFERENCES solutions(id),
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    feedback_type VARCHAR(50) NOT NULL,
                    custom_solution_description TEXT,
                    implementation_notes TEXT,
                    effectiveness_rating INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create indexes for better performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_solution_feedback_conflict_id 
                ON solution_feedback(conflict_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_solution_feedback_user_id 
                ON solution_feedback(user_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_solution_feedback_feedback_type 
                ON solution_feedback(feedback_type);
            """))
            
            print("Migration completed successfully!")
            print("Added solution_feedback table with indexes")
            
    except ProgrammingError as e:
        print(f"Migration error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during migration: {e}")
        raise

if __name__ == "__main__":
    run_migration()
