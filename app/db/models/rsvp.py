from sqlalchemy import Column, DateTime, ForeignKey, func, Enum, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum

class RSVPStatusEnum(str, enum.Enum):
    going = "going"
    interested = "interested"
    cancelled = "cancelled"

class RSVP(Base):
    __tablename__ = "rsvps"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    status = Column(Enum(RSVPStatusEnum), default=RSVPStatusEnum.going, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    event = relationship("Event")
    
    # Unique constraint to prevent duplicate RSVPs
    # Indexes for foreign keys
    __table_args__ = (
        UniqueConstraint('user_id', 'event_id', name='uq_user_event_rsvp'),
        Index('idx_rsvp_user', 'user_id'),
        Index('idx_rsvp_event', 'event_id'),
    )
