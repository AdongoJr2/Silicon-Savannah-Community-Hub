"""
Integration tests for authentication endpoints.
Tests register, login, refresh, and logout functionality with real database.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "Test123!@#",
                "full_name": "New User"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "user"
        assert "id" in data
        assert "hashed_password" not in data
    
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "weak",
                "full_name": "Test User"
            }
        )
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()
    
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with existing email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
                "full_name": "Duplicate User"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "Test123!@#",
                "full_name": "Test User"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0
    
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!@#"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        """Test refreshing access token with valid refresh token."""
        # First, login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refreshing with invalid token fails."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    async def test_refresh_with_access_token_fails(self, client: AsyncClient, test_user):
        """Test that using access token for refresh fails."""
        # Login to get access token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#"
            }
        )
        access_token = login_response.json()["access_token"]
        
        # Try to use access token for refresh (should fail)
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token}
        )
        
        assert response.status_code == 401
    
    async def test_logout_success(self, client: AsyncClient, user_token):
        """Test successful logout."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 204
    
    async def test_logout_without_token(self, client: AsyncClient):
        """Test logout without token fails."""
        response = await client.post("/api/v1/auth/logout")
        
        # HTTPBearer returns 403 when no credentials provided
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestProtectedEndpoints:
    """Test accessing protected endpoints with authentication."""
    
    async def test_access_protected_endpoint_with_valid_token(
        self, client: AsyncClient, user_token, test_user
    ):
        """Test accessing protected endpoint with valid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
    
    async def test_access_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token fails."""
        response = await client.get("/api/v1/auth/me")
        
        # HTTPBearer returns 403 when no credentials provided
        assert response.status_code == 403
    
    async def test_access_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token fails."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    async def test_organizer_only_endpoint_as_user(
        self, client: AsyncClient, user_token
    ):
        """Test accessing organizer-only endpoint as regular user fails."""
        response = await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "title": "Test Event",
                "description": "Test description",
                "location": "Test location",
                "capacity": 50
            }
        )
        
        assert response.status_code == 403
    
    async def test_organizer_only_endpoint_as_organizer(
        self, client: AsyncClient, organizer_token, mock_publish_event
    ):
        """Test accessing organizer-only endpoint as organizer succeeds."""
        response = await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {organizer_token}"},
            json={
                "title": "Test Event",
                "description": "Test description",
                "location": "Test location",
                "capacity": 50
            }
        )
        
        assert response.status_code == 200
