"""Authentication service for user management and JWT token operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import UserCreate, LoginRequest
from app.db.repositories import create_user as db_create_user, get_user_by_email as db_get_user_by_email
from app.core.security import create_access_token, create_refresh_token, verify_password, revoke_token
from fastapi import HTTPException, status


class AuthService:
    """
    Service layer for authentication operations.
    
    Handles user registration, login, token refresh, and logout operations.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize AuthService with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def register(self, payload: UserCreate):
        """
        Register a new user with password validation.
        
        Args:
            payload: User registration data containing email, password, and full_name
            
        Returns:
            Created user object
            
        Raises:
            HTTPException: If password is weak or email already exists
        """
        from app.core.security import validate_password
        try:
            validate_password(payload.password)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        existing = await db_get_user_by_email(self.session, payload.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = await db_create_user(self.session, payload)
        return user

    async def login(self, form_data: LoginRequest):
        """
        Authenticate user and generate access and refresh tokens.
        
        Args:
            form_data: Login credentials containing email and password
            
        Returns:
            Dictionary with access_token, refresh_token, and token_type
            
        Raises:
            HTTPException: If credentials are invalid
        """
        user = await db_get_user_by_email(self.session, form_data.email)
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect credentials")
        
        token_data = {"sub": str(user.id), "user_id": str(user.id), "role": user.role.value}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def refresh_access_token(self, refresh_token: str):
        """
        Generate a new access token using a valid refresh token.
        
        Args:
            refresh_token: Valid refresh token string
            
        Returns:
            Dictionary with new access_token and token_type
            
        Raises:
            HTTPException: If refresh token is invalid or wrong token type
        """
        from app.core.security import decode_token
        try:
            token_data = decode_token(refresh_token)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        if token_data.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_data = {
            "sub": token_data.get("user_id") or token_data.get("sub"),
            "user_id": token_data.get("user_id") or token_data.get("sub"),
            "role": token_data.get("role")
        }
        access_token = create_access_token(user_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    async def logout(self, token: str):
        """
        Revoke user's access token.
        
        Args:
            token: Access token to revoke
        """
        await revoke_token(token)
