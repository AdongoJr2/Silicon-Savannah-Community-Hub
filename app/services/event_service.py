from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import EventCreate
from app.db.repositories import (
    create_event as db_create_event, 
    get_event as db_get_event, 
    list_events as db_list_events,
    count_events as db_count_events
)
from app.events.publisher import publish_event
from typing import List, Optional, Tuple
from datetime import datetime

class EventService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(self, payload: EventCreate, user_id: str) -> dict:
        event = await db_create_event(self.session, payload, user_id)
        await publish_event("event.created", {"type": "event.created", "event_id": str(event.id), "created_by": str(user_id)})
        return event

    async def get_event(self, event_id: str) -> Optional[dict]:
        return await db_get_event(self.session, event_id)

    async def list_events_paginated(
        self,
        skip: int,
        limit: int,
        created_by: Optional[str],
        starts_after: Optional[datetime],
        starts_before: Optional[datetime],
        search: Optional[str],
        category: Optional[str],
    ) -> Tuple[int, List[dict]]:
        """
        List events with pagination support.
        Returns tuple of (total_count, events).
        """
        # Get total count with same filters
        total = await db_count_events(
            self.session,
            created_by=created_by,
            starts_after=starts_after,
            starts_before=starts_before,
            search=search,
            category=category,
        )
        
        # Get paginated events
        events = await db_list_events(
            self.session,
            limit=limit,
            offset=skip,
            created_by=created_by,
            starts_after=starts_after,
            starts_before=starts_before,
            search=search,
            category=category,
        )
        
        return total, events
