import pytest
import json
from fastapi import status
from unittest.mock import patch, Mock
from tests.factories import create_user, create_project, create_conflict, create_solution
from io import BytesIO


class TestProjectEndpoints:
    """Test suite for project endpoints"""
    
    @pytest.fixture
    def auth_headers(self, client, db_session):
        """Create authenticated user and return auth headers"""
        user = create_user(db_session, email="test@example.com")
        
        login_data = {
            "username": "test@example.com",
            "password": "testpassword"
        }
        
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        return {"Authorization": f"Bearer {token}"}, user
    
    def test_get_projects_empty(self, client, db_session, auth_headers):
        """Test getting projects when user has none"""
        headers, user = auth_headers
        
        response = client.get("/api/v1/projects/", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_get_projects_with_data(self, client, db_session, auth_headers):
        """Test getting projects when user has projects"""
        headers, user = auth_headers
        
        # Create projects for user
        project1 = create_project(db_session, owner=user, name="Project 1")
        project2 = create_project(db_session, owner=user, name="Project 2")
        
        response = client.get("/api/v1/projects/", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert any(p["name"] == "Project 1" for p in data)
        assert any(p["name"] == "Project 2" for p in data)
    
    def test_get_projects_unauthorized(self, client, db_session):
        """Test getting projects without authentication"""
        response = client.get("/api/v1/projects/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_project_success(self, client, db_session, auth_headers):
        """Test successful project creation"""
        headers, user = auth_headers
        
        project_data = {
            "name": "New Project",
            "description": "A test project"
        }
        
        response = client.post("/api/v1/projects/", json=project_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["status"] == "created"
        assert "id" in data
    
    def test_create_project_missing_name(self, client, db_session, auth_headers):
        """Test project creation with missing name"""
        headers, user = auth_headers
        
        project_data = {
            "description": "A test project"
        }
        
        response = client.post("/api/v1/projects/", json=project_data, headers=headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_upload_ifc_success(self, client, db_session, auth_headers, mock_ifc_content):
        """Test successful IFC file upload"""
        headers, user = auth_headers
        
        # Create project
        project = create_project(db_session, owner=user)
        
        # Mock the async task
        with patch('app.tasks.process_ifc.process_ifc_task.delay') as mock_task:
            mock_task.return_value = Mock(id="test-task-id")
            
            files = {"file": ("test.ifc", BytesIO(mock_ifc_content), "application/octet-stream")}
            
            response = client.post(
                f"/api/v1/projects/{project.id}/upload-ifc",
                files=files,
                headers=headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "IFC file uploaded successfully"
        assert "task_id" in data
        assert "model_id" in data
    
    def test_upload_ifc_wrong_extension(self, client, db_session, auth_headers):
        """Test IFC upload with wrong file extension"""
        headers, user = auth_headers
        
        # Create project
        project = create_project(db_session, owner=user)
        
        files = {"file": ("test.txt", BytesIO(b"not ifc content"), "text/plain")}
        
        response = client.post(
            f"/api/v1/projects/{project.id}/upload-ifc",
            files=files,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "IFC format" in response.json()["detail"]
    
    def test_upload_ifc_nonexistent_project(self, client, db_session, auth_headers, mock_ifc_content):
        """Test IFC upload to non-existent project"""
        headers, user = auth_headers
        
        files = {"file": ("test.ifc", BytesIO(mock_ifc_content), "application/octet-stream")}
        
        response = client.post(
            "/api/v1/projects/99999/upload-ifc",
            files=files,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_project_conflicts_empty(self, client, db_session, auth_headers):
        """Test getting conflicts when project has none"""
        headers, user = auth_headers
        
        # Create project
        project = create_project(db_session, owner=user)
        
        response = client.get(f"/api/v1/projects/{project.id}/conflicts", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_id"] == project.id
        assert data["conflicts"] == []
    
    def test_get_project_conflicts_with_data(self, client, db_session, auth_headers):
        """Test getting conflicts when project has conflicts"""
        headers, user = auth_headers
        
        # Create project and conflicts
        project = create_project(db_session, owner=user)
        conflict1 = create_conflict(db_session, project=project, conflict_type="collision")
        conflict2 = create_conflict(db_session, project=project, conflict_type="clearance")
        
        response = client.get(f"/api/v1/projects/{project.id}/conflicts", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conflicts"]) == 2
        assert any(c["type"] == "collision" for c in data["conflicts"])
        assert any(c["type"] == "clearance" for c in data["conflicts"])
    
    def test_get_project_conflicts_unauthorized_project(self, client, db_session, auth_headers):
        """Test getting conflicts for project owned by another user"""
        headers, user = auth_headers
        
        # Create project for different user
        other_user = create_user(db_session, email="other@example.com")
        project = create_project(db_session, owner=other_user)
        
        response = client.get(f"/api/v1/projects/{project.id}/conflicts", headers=headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_conflict_solutions_success(self, client, db_session, auth_headers):
        """Test getting solutions for a conflict"""
        headers, user = auth_headers
        
        # Create project, conflict, and solutions
        project = create_project(db_session, owner=user)
        conflict = create_conflict(db_session, project=project)
        solution1 = create_solution(db_session, conflict=conflict, solution_type="redesign")
        solution2 = create_solution(db_session, conflict=conflict, solution_type="relocate")
        
        response = client.get(
            f"/api/v1/projects/{project.id}/conflicts/{conflict.id}/solutions",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict_id"] == conflict.id
        assert len(data["solutions"]) == 2
        assert any(s["type"] == "redesign" for s in data["solutions"])
        assert any(s["type"] == "relocate" for s in data["solutions"])
    
    def test_get_conflict_solutions_nonexistent_conflict(self, client, db_session, auth_headers):
        """Test getting solutions for non-existent conflict"""
        headers, user = auth_headers
        
        project = create_project(db_session, owner=user)
        
        response = client.get(
            f"/api/v1/projects/{project.id}/conflicts/99999/solutions",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_submit_solution_feedback_selected_suggested(self, client, db_session, auth_headers):
        """Test submitting feedback for selected suggested solution"""
        headers, user = auth_headers
        
        # Create project, conflict, and solution
        project = create_project(db_session, owner=user)
        conflict = create_conflict(db_session, project=project)
        solution = create_solution(db_session, conflict=conflict)
        
        feedback_data = {
            "feedback_type": "selected_suggested",
            "solution_id": solution.id,
            "implementation_notes": "Worked well",
            "effectiveness_rating": 4
        }
        
        response = client.post(
            f"/api/v1/projects/{project.id}/conflicts/{conflict.id}/feedback",
            json=feedback_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Feedback submitted successfully"
        assert data["feedback_type"] == "selected_suggested"
    
    def test_submit_solution_feedback_custom_solution(self, client, db_session, auth_headers):
        """Test submitting feedback for custom solution"""
        headers, user = auth_headers
        
        # Create project and conflict
        project = create_project(db_session, owner=user)
        conflict = create_conflict(db_session, project=project)
        
        feedback_data = {
            "feedback_type": "custom_solution",
            "custom_solution_description": "I implemented a custom approach",
            "implementation_notes": "Custom solution worked better",
            "effectiveness_rating": 5
        }
        
        response = client.post(
            f"/api/v1/projects/{project.id}/conflicts/{conflict.id}/feedback",
            json=feedback_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Feedback submitted successfully"
        assert data["feedback_type"] == "custom_solution"
    
    def test_submit_solution_feedback_invalid_type(self, client, db_session, auth_headers):
        """Test submitting feedback with invalid feedback type"""
        headers, user = auth_headers
        
        project = create_project(db_session, owner=user)
        conflict = create_conflict(db_session, project=project)
        
        feedback_data = {
            "feedback_type": "invalid_type",
            "solution_id": 1
        }
        
        response = client.post(
            f"/api/v1/projects/{project.id}/conflicts/{conflict.id}/feedback",
            json=feedback_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid feedback type" in response.json()["detail"]
    
    def test_submit_solution_feedback_missing_solution_id(self, client, db_session, auth_headers):
        """Test submitting suggested solution feedback without solution ID"""
        headers, user = auth_headers
        
        project = create_project(db_session, owner=user)
        conflict = create_conflict(db_session, project=project)
        
        feedback_data = {
            "feedback_type": "selected_suggested"
        }
        
        response = client.post(
            f"/api/v1/projects/{project.id}/conflicts/{conflict.id}/feedback",
            json=feedback_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Solution ID required" in response.json()["detail"]
    
    def test_submit_solution_feedback_missing_custom_description(self, client, db_session, auth_headers):
        """Test submitting custom solution feedback without description"""
        headers, user = auth_headers
        
        project = create_project(db_session, owner=user)
        conflict = create_conflict(db_session, project=project)
        
        feedback_data = {
            "feedback_type": "custom_solution"
        }
        
        response = client.post(
            f"/api/v1/projects/{project.id}/conflicts/{conflict.id}/feedback",
            json=feedback_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Custom solution description required" in response.json()["detail"]