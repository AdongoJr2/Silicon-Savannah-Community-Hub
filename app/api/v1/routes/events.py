from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas import EventCreate, EventOut, EventCategory, PaginatedResponse, PaginationMetadata
from app.db.session import get_session
from app.services.event_service import EventService
from app.auth import get_current_user, role_required
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/events", tags=["events"])

def get_event_service(session: AsyncSession = Depends(get_session)) -> EventService:
    return EventService(session)

@router.post("/", response_model=EventOut)
async def create_event_endpoint(
    payload: EventCreate,
    user=Depends(role_required("organizer")),
    event_service: EventService = Depends(get_event_service)
):
    ev = await event_service.create_event(payload, user.id)
    return ev

@router.get("/", response_model=PaginatedResponse[EventOut])
async def get_events(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Number of items per page"),
    created_by: Optional[str] = Query(None, description="Filter by organizer user ID"),
    starts_after: Optional[datetime] = Query(None, description="Filter events starting after this datetime"),
    starts_before: Optional[datetime] = Query(None, description="Filter events starting before this datetime"),
    search: Optional[str] = Query(None, description="Search in event title and description"),
    category: Optional[EventCategory] = Query(None, description="Filter by event category"),
    event_service: EventService = Depends(get_event_service)
):
    """
    List events with pagination, filtering, and search support.
    - page: Page number, 1-indexed (default: 1)
    - per_page: Number of items per page (default: 20, max: 100)
    - created_by: Filter by organizer user ID
    - starts_after: Filter events starting after this datetime (ISO format)
    - starts_before: Filter events starting before this datetime (ISO format)
    - search: Full-text search in event title and description
    - category: Filter by event category (technology, business, arts, sports, etc.)
    """
    # Calculate skip/offset from page number
    skip = (page - 1) * per_page
    
    # Get total count and events
    total_count, events = await event_service.list_events_paginated(
        skip=skip,
        limit=per_page,
        created_by=created_by,
        starts_after=starts_after,
        starts_before=starts_before,
        search=search,
        category=category.value if category else None,
    )
    
    # Calculate pagination metadata
    total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
    
    return PaginatedResponse(
        items=events,
        pagination=PaginationMetadata(
            total=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    )

@router.get("/{event_id}", response_model=EventOut)
async def get_event_detail(
    event_id: str,
    event_service: EventService = Depends(get_event_service)
):
    ev = await event_service.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev
