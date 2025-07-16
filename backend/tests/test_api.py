import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Vitruvius API"}

def test_health_check():
    """Test that the API is running"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()