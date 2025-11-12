"""
Unit tests for repository functions.
Tests user creation, event CRUD operations, and RSVP management.
"""
import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException

from app.db.repositories import (
    create_user,
    get_user_by_email,
    get_user,
    create_event,
    list_events,
    get_event,
    get_event_rsvp_count,
    create_rsvp,
    list_rsvps_for_event,
)
from app.schemas import UserCreate, EventCreate, RSVPCreate
from app.db.models import User, Event, RSVP, RoleEnum, RSVPStatusEnum


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserRepository:
    """Test user repository functions."""
    
    async def test_create_user(self, db_session):
        """Test creating a new user."""
        user_data = UserCreate(
            email="newuser@example.com",
            password="Test123!@#",
            full_name="New User"
        )
        
        user = await create_user(db_session, user_data)
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.role == RoleEnum.user
        assert user.hashed_password != "Test123!@#"  # Should be hashed
    
    async def test_get_user_by_email(self, db_session, test_user):
        """Test retrieving user by email."""
        user = await get_user_by_email(db_session, test_user.email)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    async def test_get_user_by_email_not_found(self, db_session):
        """Test retrieving non-existent user returns None."""
        user = await get_user_by_email(db_session, "nonexistent@example.com")
        
        assert user is None
    
    async def test_get_user_by_id(self, db_session, test_user):
        """Test retrieving user by ID."""
        user = await get_user(db_session, test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    async def test_get_user_by_id_not_found(self, db_session):
        """Test retrieving user with invalid ID returns None."""
        from uuid import uuid4
        user = await get_user(db_session, uuid4())
        
        assert user is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventRepository:
    """Test event repository functions."""
    
    async def test_create_event(self, db_session, test_organizer):
        """Test creating a new event."""
        event_data = EventCreate(
            title="New Event",
            description="Event description",
            location="Event location",
            starts_at=datetime.utcnow() + timedelta(days=7),
            capacity=100
        )
        
        event = await create_event(db_session, event_data, test_organizer.id)
        
        assert event.id is not None
        assert event.title == "New Event"
        assert event.description == "Event description"
        assert event.capacity == 100
        assert event.created_by == test_organizer.id
    
    async def test_list_events(self, db_session, test_events):
        """Test listing events with pagination."""
        events = await list_events(db_session, limit=3, offset=0)
        
        assert len(events) == 3
        assert all(isinstance(e, dict) for e in events)
        assert all('id' in e and 'title' in e for e in events)
    
    async def test_list_events_with_offset(self, db_session, test_events):
        """Test listing events with offset."""
        events = await list_events(db_session, limit=2, offset=2)
        
        assert len(events) == 2
    
    async def test_list_events_filter_by_creator(self, db_session, test_organizer, test_events):
        """Test filtering events by creator."""
        events = await list_events(db_session, created_by=str(test_organizer.id))
        
        assert len(events) == len(test_events)
        assert all(e['created_by'] == str(test_organizer.id) for e in events)
    
    async def test_list_events_filter_by_date_range(self, db_session, test_events):
        """Test filtering events by date range."""
        now = datetime.utcnow()
        after = now + timedelta(days=2)
        before = now + timedelta(days=4)
        
        events = await list_events(
            db_session,
            starts_after=after,
            starts_before=before
        )
        
        # Should get events that start between day 2 and day 4
        assert len(events) >= 1
    
    async def test_get_event(self, db_session, test_event):
        """Test retrieving a single event."""
        event = await get_event(db_session, str(test_event.id))
        
        assert event is not None
        assert event['id'] == str(test_event.id)
        assert event['title'] == test_event.title
    
    async def test_get_event_not_found(self, db_session):
        """Test retrieving non-existent event returns None."""
        from uuid import uuid4
        event = await get_event(db_session, str(uuid4()))
        
        assert event is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestRSVPRepository:
    """Test RSVP repository functions."""
    
    async def test_create_rsvp(self, db_session, test_user, test_event):
        """Test creating an RSVP."""
        rsvp_data = RSVPCreate(
            event_id=test_event.id,
            status="going"
        )
        
        rsvp = await create_rsvp(db_session, test_user.id, rsvp_data)
        
        assert rsvp.id is not None
        assert rsvp.user_id == test_user.id
        assert rsvp.event_id == test_event.id
        assert rsvp.status == RSVPStatusEnum.going
    
    async def test_create_rsvp_event_not_found(self, db_session, test_user):
        """Test creating RSVP for non-existent event raises error."""
        from uuid import uuid4
        
        rsvp_data = RSVPCreate(
            event_id=uuid4(),
            status="going"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_rsvp(db_session, test_user.id, rsvp_data)
        
        assert exc_info.value.status_code == 404
        assert "Event not found" in str(exc_info.value.detail)
    
    async def test_create_rsvp_exceeds_capacity(self, db_session, test_user, test_organizer):
        """Test creating RSVP when event is at capacity."""
        # Create event with capacity of 1
        event_data = EventCreate(
            title="Small Event",
            description="Event with limited capacity",
            location="Test location",
            starts_at=datetime.utcnow() + timedelta(days=1),
            capacity=1
        )
        event = await create_event(db_session, event_data, test_organizer.id)
        
        # Create first RSVP (should succeed)
        rsvp_data1 = RSVPCreate(event_id=event.id, status="going")
        await create_rsvp(db_session, test_user.id, rsvp_data1)
        
        # Create second user and try to RSVP (should fail)
        user2 = User(
            email="user2@example.com",
            hashed_password="hashed",
            full_name="User 2",
            role=RoleEnum.user
        )
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user2)
        
        rsvp_data2 = RSVPCreate(event_id=event.id, status="going")
        
        with pytest.raises(HTTPException) as exc_info:
            await create_rsvp(db_session, user2.id, rsvp_data2)
        
        assert exc_info.value.status_code == 400
        assert "full capacity" in str(exc_info.value.detail)
    
    async def test_get_event_rsvp_count(self, db_session, test_event, test_rsvp):
        """Test counting RSVPs for an event."""
        count = await get_event_rsvp_count(db_session, str(test_event.id))
        
        assert count == 1
    
    async def test_get_event_rsvp_count_only_counts_going(self, db_session, test_user, test_event):
        """Test that RSVP count only includes 'going' status."""
        # Create 'interested' RSVP (should not be counted)
        rsvp_data = RSVPCreate(event_id=test_event.id, status="interested")
        await create_rsvp(db_session, test_user.id, rsvp_data)
        
        count = await get_event_rsvp_count(db_session, str(test_event.id))
        
        assert count == 0  # 'interested' should not be counted
    
    async def test_list_rsvps_for_event(self, db_session, test_event, test_rsvp):
        """Test listing RSVPs for an event."""
        rsvps = await list_rsvps_for_event(db_session, str(test_event.id))
        
        assert len(rsvps) == 1
        assert rsvps[0].id == test_rsvp.id
    
    async def test_list_rsvps_for_event_empty(self, db_session, test_event):
        """Test listing RSVPs for event with no RSVPs."""
        rsvps = await list_rsvps_for_event(db_session, str(test_event.id))
        
        assert len(rsvps) == 0
