from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import RSVPCreate
from app.db.repositories import create_rsvp as db_create_rsvp
from app.events.publisher import publish_event

class RSVPService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_rsvp(self, payload: RSVPCreate, user_id: str) -> dict:
        rsvp = await db_create_rsvp(self.session, user_id, payload)
        await publish_event("rsvp.created", {"type": "rsvp.created", "rsvp_id": str(rsvp.id), "user_id": str(user_id), "event_id": str(rsvp.event_id)})
        return rsvp
