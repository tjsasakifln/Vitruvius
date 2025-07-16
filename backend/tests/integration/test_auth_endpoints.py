import pytest
from fastapi import status
from tests.factories import create_user


class TestAuthEndpoints:
    """Test suite for authentication endpoints"""
    
    def test_register_user_success(self, client, db_session):
        """Test successful user registration"""
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "hashed_password" not in data  # Should not return password
    
    def test_register_user_duplicate_email(self, client, db_session):
        """Test registration with duplicate email"""
        # Create user in database
        create_user(db_session, email="test@example.com")
        
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"]
    
    def test_register_user_invalid_email(self, client, db_session):
        """Test registration with invalid email"""
        user_data = {
            "email": "invalid-email",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_user_missing_password(self, client, db_session):
        """Test registration with missing password"""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_success(self, client, db_session):
        """Test successful login"""
        # Create user
        user = create_user(db_session, email="test@example.com")
        
        login_data = {
            "username": "test@example.com",
            "password": "testpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client, db_session):
        """Test login with invalid credentials"""
        # Create user
        create_user(db_session, email="test@example.com")
        
        login_data = {
            "username": "test@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, client, db_session):
        """Test login with non-existent user"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "testpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_success(self, client, db_session):
        """Test getting current user info"""
        # Create user and login
        user = create_user(db_session, email="test@example.com")
        
        login_data = {
            "username": "test@example.com",
            "password": "testpassword"
        }
        
        login_response = client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user.email
        assert data["id"] == user.id
    
    def test_get_current_user_unauthorized(self, client, db_session):
        """Test getting current user without authentication"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_invalid_token(self, client, db_session):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED