"""Authentication routes for user registration, login, logout, and token management."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas import UserCreate, UserOut, Token, TokenResponse, LoginRequest, RefreshTokenRequest
from app.services.auth_service import AuthService
from app.db.session import get_session
from app.db.models.user import User
from app.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()

def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    """
    Dependency injection for AuthService.
    
    Args:
        session: Database session
        
    Returns:
        AuthService instance
    """
    return AuthService(session)

@router.post("/register", response_model=UserOut)
@limiter.limit("3/minute")
async def register(
    request: Request, 
    payload: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.
    
    Rate limit: 3 requests per minute
    
    Args:
        request: FastAPI request object (for rate limiting)
        payload: User registration data
        auth_service: Authentication service instance
        
    Returns:
        Created user object
        
    Raises:
        HTTPException: If email already exists or password is weak
    """
    user = await auth_service.register(payload)
    return user

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request, 
    form_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login endpoint returning access and refresh tokens.
    
    Rate limit: 5 requests per minute
    
    Args:
        request: FastAPI request object (for rate limiting)
        form_data: User login credentials
        auth_service: Authentication service instance
        
    Returns:
        Access and refresh tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    return await auth_service.login(form_data)

@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_access_token(
    request: Request, 
    payload: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.
    
    Rate limit: 10 requests per minute
    
    Args:
        request: FastAPI request object (for rate limiting)
        payload: Refresh token request
        auth_service: Authentication service instance
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    return await auth_service.refresh_access_token(payload.refresh_token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user by revoking their current token.
    Requires valid access token in Authorization header.
    """
    await auth_service.logout(credentials.credentials)
    return None


@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information from JWT token.
    
    Returns:
        Current user details
    """
    return current_user
