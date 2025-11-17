"""
Repository layer for database operations.

Provides async functions for CRUD operations on User, Event, and RSVP entities.
Includes caching support via Redis for frequently accessed data.
"""
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.db.models.event import Event
from app.db.models.rsvp import RSVP, RSVPStatusEnum
from app.schemas import UserCreate, EventCreate, RSVPCreate
from typing import Optional, List
from app.cache.cache_decorators import cached
from app.cache.redis_client import cache
from app.core.security import hash_password
from datetime import datetime
import uuid


async def create_user(db: AsyncSession, user_in: UserCreate):
    """
    Create a new user with hashed password.
    
    Args:
        db: Database session
        user_in: User registration data
        
    Returns:
        Created User object
    """
    hashed = hash_password(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed, full_name=user_in.full_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Retrieve user by email address.
    
    Args:
        db: Database session
        email: User's email address
        
    Returns:
        User object if found, None otherwise
    """
    q = select(User).where(User.email == email)
    res = await db.execute(q)
    return res.scalars().first()

async def get_user(db: AsyncSession, user_id):
    """
    Retrieve user by ID.
    
    Args:
        db: Database session
        user_id: User's UUID
        
    Returns:
        User object if found, None otherwise
    """
    q = select(User).where(User.id == user_id)
    res = await db.execute(q)
    return res.scalars().first()

async def create_event(db: AsyncSession, payload: EventCreate, creator_id):
    """
    Create a new event and invalidate events cache.
    
    Args:
        db: Database session
        payload: Event creation data
        creator_id: UUID of user creating the event
        
    Returns:
        Created Event object
    """
    ev = Event(**payload.dict(), created_by=creator_id)
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    
    # Invalidate events list cache
    await cache.delete_pattern("events:list:*")
    
    return ev

@cached('events:list', expire=300)  # Cache for 5 minutes
async def list_events(
    db: AsyncSession, 
    limit: int = 20, 
    offset: int = 0,
    created_by: Optional[str] = None,
    starts_after: Optional[datetime] = None,
    starts_before: Optional[datetime] = None,
    search: Optional[str] = None,
    category: Optional[str] = None
) -> List[dict]:
    """
    List events with pagination, filtering, and search support.
    Returns a list of event dictionaries for caching compatibility.
    """
    q = select(Event).order_by(Event.created_at.desc())
    
    # Apply filters
    if created_by:
        q = q.where(Event.created_by == created_by)
    if starts_after:
        q = q.where(Event.starts_at >= starts_after)
    if starts_before:
        q = q.where(Event.starts_at <= starts_before)
    if category:
        q = q.where(Event.category == category)
    
    # Apply full-text search
    if search:
        # Use PostgreSQL full-text search with to_tsvector
        search_vector = func.to_tsvector('english', 
            func.coalesce(Event.title, '') + ' ' + func.coalesce(Event.description, ''))
        search_query = func.plainto_tsquery('english', search)
        q = q.where(search_vector.op('@@')(search_query))
    
    # Apply pagination
    q = q.limit(limit).offset(offset)
    
    res = await db.execute(q)
    events = res.scalars().all()
    
    # Convert to list of dicts for caching, calculate available spots
    result = []
    for ev in events:
        rsvp_count = await get_event_rsvp_count(db, str(ev.id))
        available_spots = None
        if ev.capacity and ev.capacity > 0:
            available_spots = max(0, ev.capacity - rsvp_count)
        
        result.append({
            'id': str(ev.id),
            'title': ev.title,
            'description': ev.description,
            'location': ev.location,
            'starts_at': ev.starts_at.isoformat() if ev.starts_at else None,
            'capacity': ev.capacity,
            'category': ev.category.value if ev.category else None,
            'created_by': str(ev.created_by),
            'created_at': ev.created_at.isoformat() if ev.created_at else None,
            'available_spots': available_spots
        })
    
    return result

@cached('events:count', expire=300)  # Cache for 5 minutes
async def count_events(
    db: AsyncSession,
    created_by: Optional[str] = None,
    starts_after: Optional[datetime] = None,
    starts_before: Optional[datetime] = None,
    search: Optional[str] = None,
    category: Optional[str] = None
) -> int:
    """
    Count total events matching the given filters.
    Used for pagination metadata.
    """
    q = select(func.count(Event.id))
    
    # Apply same filters as list_events
    if created_by:
        q = q.where(Event.created_by == created_by)
    if starts_after:
        q = q.where(Event.starts_at >= starts_after)
    if starts_before:
        q = q.where(Event.starts_at <= starts_before)
    if category:
        q = q.where(Event.category == category)
    
    # Apply full-text search
    if search:
        search_vector = func.to_tsvector('english', 
            func.coalesce(Event.title, '') + ' ' + func.coalesce(Event.description, ''))
        search_query = func.plainto_tsquery('english', search)
        q = q.where(search_vector.op('@@')(search_query))
    
    res = await db.execute(q)
    return res.scalar() or 0

@cached('events:detail', expire=300)  # Cache for 5 minutes
async def get_event(db: AsyncSession, event_id):
    q = select(Event).where(Event.id == event_id)
    res = await db.execute(q)
    ev = res.scalars().first()
    if ev:
        # Calculate available spots
        rsvp_count = await get_event_rsvp_count(db, str(ev.id))
        available_spots = None
        if ev.capacity and ev.capacity > 0:
            available_spots = max(0, ev.capacity - rsvp_count)
        
        # Convert to dict for caching
        return {
            'id': str(ev.id),
            'title': ev.title,
            'description': ev.description,
            'location': ev.location,
            'starts_at': ev.starts_at.isoformat() if ev.starts_at else None,
            'capacity': ev.capacity,
            'category': ev.category.value if ev.category else None,
            'created_by': str(ev.created_by),
            'created_at': ev.created_at.isoformat() if ev.created_at else None,
            'available_spots': available_spots
        }
    return None

async def get_event_rsvp_count(db: AsyncSession, event_id: str) -> int:
    """Get the count of confirmed RSVPs (going) for an event."""
    q = select(func.count(RSVP.id)).where(
        RSVP.event_id == event_id,
        RSVP.status == RSVPStatusEnum.going
    )
    res = await db.execute(q)
    return res.scalar() or 0

async def create_rsvp(db: AsyncSession, user_id, payload: RSVPCreate):
    """
    Create an RSVP with capacity validation.
    Raises HTTPException if event is at capacity or user already has an RSVP.
    """
    from fastapi import HTTPException
    from sqlalchemy.exc import IntegrityError
    
    # Get the event to check capacity
    event_q = select(Event).where(Event.id == payload.event_id)
    event_res = await db.execute(event_q)
    event = event_res.scalars().first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check capacity if event has a capacity limit and RSVP status is "going"
    if event.capacity and event.capacity > 0 and payload.status == "going":
        current_count = await get_event_rsvp_count(db, payload.event_id)
        if current_count >= event.capacity:
            raise HTTPException(
                status_code=400, 
                detail=f"Event is at full capacity ({event.capacity} attendees)"
            )
    
    # Create the RSVP
    r = RSVP(user_id=user_id, event_id=payload.event_id, status=payload.status)
    db.add(r)
    
    try:
        await db.commit()
        await db.refresh(r)
    except IntegrityError as e:
        await db.rollback()
        # Check if it's a unique constraint violation for user+event
        if "uq_user_event_rsvp" in str(e.orig) or "duplicate key" in str(e.orig).lower():
            raise HTTPException(
                status_code=409,
                detail="You have already RSVP'd to this event. Please update your existing RSVP instead."
            )
        # Re-raise if it's a different integrity error
        raise HTTPException(status_code=400, detail="Database constraint violation")
    
    # Invalidate event caches since RSVP count affects available_spots
    await cache.delete_pattern("events:list:*")
    await cache.delete(f"events:detail:{payload.event_id}")
    
    return r

async def list_rsvps_for_event(db: AsyncSession, event_id):
    q = select(RSVP).where(RSVP.event_id == event_id)
    res = await db.execute(q)
    return res.scalars().all()

async def get_user_rsvp_for_event(db: AsyncSession, user_id: uuid.UUID, event_id: uuid.UUID) -> Optional[RSVP]:
    """
    Get a user's RSVP for a specific event.
    
    Args:
        db: Database session
        user_id: User's UUID
        event_id: Event's UUID
        
    Returns:
        RSVP object if found, None otherwise
    """
    q = select(RSVP).where(
        RSVP.user_id == user_id,
        RSVP.event_id == event_id
    )
    res = await db.execute(q)
    return res.scalars().first()
