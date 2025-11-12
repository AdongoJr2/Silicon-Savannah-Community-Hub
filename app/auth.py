from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.user import User
from app.core.security import decode_token, is_token_revoked, validate_password, verify_password, create_access_token

# Use HTTPBearer for JWT token authentication instead of OAuth2PasswordBearer
# This will show a simple "Authorize" button in Swagger UI where you can paste your JWT token
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Get current user from JWT token with revocation check.
    
    Args:
        credentials: HTTP Bearer credentials containing the JWT token
        session: Database session (injected)
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or revoked
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is revoked
    if await is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    try:
        payload = decode_token(token)
    except ValueError:
        raise credentials_exception
    
    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user_id from sub claim (standard JWT) or fall back to user_id
    user_id: Optional[str] = payload.get("sub") or payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    # Fetch user
    q = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = q.scalars().first()
    if not user:
        raise credentials_exception
    return user


def role_required(required_role: str):
    """
    Dependency to require specific role for endpoint access.
    
    Args:
        required_role: Role name required (e.g., 'organizer')
        
    Returns:
        Dependency function
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if getattr(user, "role", None) != required_role and getattr(user, "role", None) != "admin":
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return role_checker
