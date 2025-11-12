from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum

class EventCategory(str, enum.Enum):
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

class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    capacity = Column(Integer, nullable=True, default=0)
    category = Column(Enum(EventCategory), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User")
    
    # Indexes for frequently queried fields
    __table_args__ = (
        Index('idx_event_date', 'starts_at'),
        Index('idx_event_organizer', 'created_by'),
        Index('idx_event_created_at', 'created_at'),
        Index('idx_event_category', 'category'),
    )
