from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas import EventCreate, EventOut, EventCategory
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

@router.get("/", response_model=List[EventOut])
async def get_events(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    created_by: Optional[str] = Query(None, description="Filter by organizer user ID"),
    starts_after: Optional[datetime] = Query(None, description="Filter events starting after this datetime"),
    starts_before: Optional[datetime] = Query(None, description="Filter events starting before this datetime"),
    search: Optional[str] = Query(None, description="Search in event title and description"),
    category: Optional[EventCategory] = Query(None, description="Filter by event category"),
    event_service: EventService = Depends(get_event_service)
):
    """
    List events with pagination, filtering, and search support.
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 20, max: 100)
    - created_by: Filter by organizer user ID
    - starts_after: Filter events starting after this datetime (ISO format)
    - starts_before: Filter events starting before this datetime (ISO format)
    - search: Full-text search in event title and description
    - category: Filter by event category (technology, business, arts, sports, etc.)
    """
    events = await event_service.list_events(
        skip=skip,
        limit=limit,
        created_by=created_by,
        starts_after=starts_after,
        starts_before=starts_before,
        search=search,
        category=category.value if category else None,
    )
    return events

@router.get("/{event_id}", response_model=EventOut)
async def get_event_detail(
    event_id: str,
    event_service: EventService = Depends(get_event_service)
):
    ev = await event_service.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev
