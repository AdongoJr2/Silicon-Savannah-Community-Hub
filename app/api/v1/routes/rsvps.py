from fastapi import APIRouter, Depends, HTTPException
from app.schemas import RSVPCreate, RSVPOut
from app.db.session import get_session
from app.services.rsvp_service import RSVPService
from app.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter(prefix="/rsvps", tags=["rsvps"])

def get_rsvp_service(session: AsyncSession = Depends(get_session)) -> RSVPService:
    return RSVPService(session)

@router.post("/", response_model=RSVPOut)
async def create_rsvp_endpoint(
    payload: RSVPCreate,
    user=Depends(get_current_user),
    rsvp_service: RSVPService = Depends(get_rsvp_service)
):
    r = await rsvp_service.create_rsvp(payload, user.id)
    return r
