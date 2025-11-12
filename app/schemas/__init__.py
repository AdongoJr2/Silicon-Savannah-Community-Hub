from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class EventCategory(str, Enum):
    """Event category/tag enum."""
    technology = "technology"
    business = "business"
    arts = "arts"
    sports = "sports"
    education = "education"
    social = "social"
    health = "health"
    music = "music"
    food = "food"
    other = "other"

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenResponse(BaseModel):
    """Enhanced token response with refresh token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    """Schema for user login request."""
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str]
    role: str

    class Config:
        from_attributes = True

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    starts_at: Optional[datetime] = None
    capacity: Optional[int] = 0
    category: Optional[EventCategory] = None

class EventOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    location: Optional[str]
    starts_at: Optional[datetime]
    capacity: Optional[int]
    category: Optional[EventCategory]
    created_by: UUID
    available_spots: Optional[int] = None

    class Config:
        from_attributes = True

class RSVPCreate(BaseModel):
    event_id: UUID
    status: Optional[str] = "going"

class RSVPOut(BaseModel):
    id: UUID
    user_id: UUID
    event_id: UUID
    status: str

    class Config:
        from_attributes = True
