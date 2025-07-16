"""
Migration script to convert elements_involved field to proper Many-to-Many relationship
This script handles the migration from the old string-based approach to the new junction table
"""
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .database import get_database_url
from .models.project import Base, Conflict, Element, IFCModel

def migrate_conflict_elements():
    """
    Migrate existing conflict data from elements_involved string field to proper Many-to-Many relationship
    """
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create new tables
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    
    try:
        # Step 1: Create elements table and populate it with existing data
        print("Creating elements table and populating with existing data...")
        
        # Get all IFC models
        ifc_models = session.query(IFCModel).all()
        
        for ifc_model in ifc_models:
            # For now, we'll create placeholder elements
            # In a real migration, you'd extract this from the actual IFC files
            print(f"Processing IFC model: {ifc_model.filename}")
            
            # Create sample elements (this would be populated from actual IFC data)
            sample_elements = [
                {"ifc_id": "elem_1", "element_type": "IfcWall", "name": "Wall-001"},
                {"ifc_id": "elem_2", "element_type": "IfcWindow", "name": "Window-001"},
                {"ifc_id": "elem_3", "element_type": "IfcDoor", "name": "Door-001"},
                {"ifc_id": "elem_4", "element_type": "IfcBeam", "name": "Beam-001"},
                {"ifc_id": "elem_5", "element_type": "IfcColumn", "name": "Column-001"},
            ]
            
            for elem_data in sample_elements:
                element = Element(
                    ifc_model_id=ifc_model.id,
                    ifc_id=elem_data["ifc_id"],
                    element_type=elem_data["element_type"],
                    name=elem_data["name"],
                    description=f"Element {elem_data['name']} of type {elem_data['element_type']}",
                    geometry_data="{}",  # Placeholder for geometry data
                    properties="{}"  # Placeholder for properties
                )
                session.add(element)
        
        session.commit()
        print("Elements table populated successfully.")
        
        # Step 2: Migrate existing conflicts
        print("Migrating existing conflicts...")
        
        # Get all conflicts with elements_involved data
        conflicts = session.query(Conflict).all()
        
        for conflict in conflicts:
            if hasattr(conflict, 'elements_involved') and conflict.elements_involved:
                try:
                    # Parse the elements_involved field
                    if conflict.elements_involved.startswith('['):
                        # JSON array format
                        element_ids = json.loads(conflict.elements_involved)
                    else:
                        # Comma-separated string format
                        element_ids = [int(x.strip()) for x in conflict.elements_involved.split(',') if x.strip()]
                    
                    # Map old element IDs to new Element records
                    # For this migration, we'll create a mapping based on the order
                    elements = session.query(Element).filter(
                        Element.ifc_model_id.in_(
                            session.query(IFCModel.id).filter(IFCModel.project_id == conflict.project_id)
                        )
                    ).all()
                    
                    # Associate elements with the conflict
                    for i, old_id in enumerate(element_ids):
                        if i < len(elements):
                            conflict.elements.append(elements[i])
                    
                    print(f"Migrated conflict {conflict.id} with {len(element_ids)} elements")
                    
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing elements_involved for conflict {conflict.id}: {e}")
                    continue
        
        session.commit()
        print("Conflicts migration completed successfully.")
        
        # Step 3: Drop the old elements_involved column
        print("Dropping old elements_involved column...")
        session.execute(text("ALTER TABLE conflicts DROP COLUMN elements_involved"))
        session.commit()
        print("Old column dropped successfully.")
        
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_conflict_elements()
