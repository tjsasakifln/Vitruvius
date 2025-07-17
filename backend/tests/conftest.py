import pytest
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.db.models.project import Base
from app.db.database import get_db
from app.core.config import settings


@pytest.fixture(scope="session")
def test_db():
    """Create test database for the entire test session"""
    # Use in-memory SQLite for faster tests
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create a fresh database session for each test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session dependency override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def temp_file(tmp_path):
    """Create a temporary file within a pytest-managed directory."""
    temp_dir = tmp_path / "uploads"
    temp_dir.mkdir()
    temp_file = temp_dir / "test.ifc"
    temp_file.write_bytes(b"fake IFC content for testing")
    yield str(temp_file)
    # Cleanup is managed automatically by pytest


@pytest.fixture(scope="function")
def persistent_temp_file(tmp_path):
    """Create a temporary file that persists for async tasks."""
    temp_dir = tmp_path / "uploads"
    temp_dir.mkdir()
    temp_file = temp_dir / "persistent_test.ifc"
    
    # Write more realistic IFC content
    ifc_content = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'), '2;1');
FILE_NAME('test.ifc', '2024-01-01T00:00:00', ('Test'), ('Test'), 'Test', 'Test', '');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1 = IFCPROJECT('test', $, 'Test Project', $, $, $, $, $, $);
#2 = IFCWALL('wall1', $, 'Wall 1', $, $, $, $, $, $);
#3 = IFCCOLUMN('col1', $, 'Column 1', $, $, $, $, $, $);
ENDSEC;
END-ISO-10303-21;"""
    
    temp_file.write_bytes(ifc_content)
    yield str(temp_file)
    # Cleanup is managed automatically by pytest


@pytest.fixture
def mock_ifc_content():
    """Mock IFC file content for testing"""
    return b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'), '2;1');
FILE_NAME('test.ifc', '2024-01-01T00:00:00', ('Test'), ('Test'), 'Test', 'Test', '');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1 = IFCPROJECT('test', $, 'Test Project', $, $, $, $, $, $);
ENDSEC;
END-ISO-10303-21;"""