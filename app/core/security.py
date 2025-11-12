"""
Enhanced security module with JWT access and refresh tokens.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
from app.cache.redis_client import cache

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password(password: str) -> None:
    """
    Validate password strength.
    Raises ValueError if password doesn't meet requirements.
    
    Args:
        password: The password to validate
        
    Raises:
        ValueError: If password doesn't meet strength requirements
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        raise ValueError("Password must contain at least one special character")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        data: Data to encode in the token
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token data
        
    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Validate required fields
        if "sub" not in payload:
            raise ValueError("Invalid token payload: missing 'sub' field")
        
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except JWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")


async def revoke_token(token: str, expiry: Optional[int] = None) -> bool:
    """
    Add token to revocation list in Redis.
    
    Args:
        token: Token to revoke
        expiry: Optional TTL in seconds (if not provided, calculated from token exp)
        
    Returns:
        True if successful
    """
    try:
        if expiry:
            # Use provided expiry
            await cache.set(f"revoked_token:{token}", True, expire=expiry)
        else:
            # Calculate TTL from token
            payload = decode_token(token)
            exp = payload.get("exp")
            if exp:
                ttl = exp - int(datetime.utcnow().timestamp())
                if ttl > 0:
                    await cache.set(f"revoked_token:{token}", True, expire=ttl)
        
        return True
    except Exception:
        return False


async def is_token_revoked(token: str) -> bool:
    """
    Check if token is in revocation list.
    
    Args:
        token: Token to check
        
    Returns:
        True if token is revoked
    """
    return await cache.exists(f"revoked_token:{token}")
