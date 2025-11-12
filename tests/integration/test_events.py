"""
Integration tests for events endpoints.
Tests event CRUD, filtering, pagination, search, and capacity management.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


@pytest.mark.integration
@pytest.mark.asyncio
class TestEventEndpoints:
    """Test event API endpoints."""
    
    async def test_create_event_as_organizer(
        self, client: AsyncClient, organizer_token, mock_publish_event
    ):
        """Test creating an event as organizer."""
        response = await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {organizer_token}"},
            json={
                "title": "Tech Conference",
                "description": "A great tech conference",
                "location": "Convention Center",
                "capacity": 100,
                "category": "technology"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Tech Conference"
        assert data["capacity"] == 100
        assert data["category"] == "technology"
        assert "id" in data
    
    async def test_create_event_as_user_fails(
        self, client: AsyncClient, user_token
    ):
        """Test that regular users cannot create events."""
        response = await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "title": "Test Event",
                "description": "Description",
                "location": "Location",
                "capacity": 50
            }
        )
        
        assert response.status_code == 403
    
    async def test_list_events(self, client: AsyncClient, test_events):
        """Test listing events."""
        response = await client.get("/api/v1/events/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all("id" in event and "title" in event for event in data)
    
    async def test_list_events_pagination(
        self, client: AsyncClient, test_events
    ):
        """Test event list pagination."""
        # Get first page
        response1 = await client.get("/api/v1/events/?skip=0&limit=2")
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1) == 2
        
        # Get second page
        response2 = await client.get("/api/v1/events/?skip=2&limit=2")
        assert response2.status_code == 200
        page2 = response2.json()
        assert len(page2) == 2
        
        # Verify different events
        assert page1[0]["id"] != page2[0]["id"]
    
    async def test_list_events_filter_by_category(
        self, client: AsyncClient, organizer_token, mock_publish_event
    ):
        """Test filtering events by category."""
        # Create events with different categories
        await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {organizer_token}"},
            json={
                "title": "Tech Event",
                "description": "Tech desc",
                "location": "Location",
                "capacity": 50,
                "category": "technology"
            }
        )
        
        await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {organizer_token}"},
            json={
                "title": "Sports Event",
                "description": "Sports desc",
                "location": "Stadium",
                "capacity": 100,
                "category": "sports"
            }
        )
        
        # Filter by technology category
        response = await client.get("/api/v1/events/?category=technology")
        assert response.status_code == 200
        events = response.json()
        assert all(e["category"] == "technology" for e in events if e.get("category"))
    
    async def test_list_events_search(
        self, client: AsyncClient, organizer_token, mock_publish_event
    ):
        """Test full-text search on events."""
        # Create event with specific keywords
        await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {organizer_token}"},
            json={
                "title": "Python Workshop",
                "description": "Learn Python programming",
                "location": "Tech Center",
                "capacity": 30
            }
        )
        
        # Search for "python"
        response = await client.get("/api/v1/events/?search=python")
        assert response.status_code == 200
        events = response.json()
        assert len(events) > 0
        # Verify at least one event matches
        assert any("python" in e["title"].lower() or 
                  ("description" in e and e["description"] and "python" in e["description"].lower())
                  for e in events)
    
    async def test_get_event_detail(self, client: AsyncClient, test_event):
        """Test getting event details."""
        response = await client.get(f"/api/v1/events/{test_event.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_event.id)
        assert data["title"] == test_event.title
        assert "available_spots" in data
    
    async def test_get_event_not_found(self, client: AsyncClient):
        """Test getting non-existent event returns 404."""
        from uuid import uuid4
        response = await client.get(f"/api/v1/events/{uuid4()}")
        
        assert response.status_code == 404
    
    async def test_event_available_spots_calculation(
        self, client: AsyncClient, test_event, test_rsvp
    ):
        """Test that available_spots is calculated correctly."""
        response = await client.get(f"/api/v1/events/{test_event.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        if test_event.capacity and test_event.capacity > 0:
            # Should be capacity - 1 (test_rsvp is 'going')
            assert data["available_spots"] == test_event.capacity - 1


@pytest.mark.integration
@pytest.mark.asyncio
class TestEventCapacity:
    """Test event capacity management."""
    
    async def test_rsvp_to_event_with_capacity(
        self, client: AsyncClient, user_token, organizer_token, mock_publish_event
    ):
        """Test RSVPing to event with available capacity."""
        # Create event with capacity
        event_response = await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {organizer_token}"},
            json={
                "title": "Limited Event",
                "description": "Event with capacity",
                "location": "Venue",
                "capacity": 5
            }
        )
        event = event_response.json()
        
        # RSVP to event
        rsvp_response = await client.post(
            "/api/v1/rsvps/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "event_id": event["id"],
                "status": "going"
            }
        )
        
        assert rsvp_response.status_code == 200
    
    async def test_rsvp_to_full_event_fails(
        self, client: AsyncClient, organizer_token, db_session, mock_publish_event
    ):
        """Test RSVPing to full event fails."""
        from app.db.models import User, RoleEnum
        from app.core.security import hash_password, create_access_token
        
        # Create event with capacity of 1
        event_response = await client.post(
            "/api/v1/events/",
            headers={"Authorization": f"Bearer {organizer_token}"},
            json={
                "title": "Tiny Event",
                "description": "Event with 1 spot",
                "location": "Small Room",
                "capacity": 1
            }
        )
        event = event_response.json()
        
        # Create first user and RSVP
        user1 = User(
            email="user1@example.com",
            hashed_password=hash_password("Test123!@#"),
            full_name="User 1",
            role=RoleEnum.user
        )
        db_session.add(user1)
        await db_session.commit()
        await db_session.refresh(user1)
        
        token1 = create_access_token({"sub": str(user1.id), "role": "user"})
        
        rsvp1_response = await client.post(
            "/api/v1/rsvps/",
            headers={"Authorization": f"Bearer {token1}"},
            json={"event_id": event["id"], "status": "going"}
        )
        assert rsvp1_response.status_code == 200
        
        # Create second user and try to RSVP (should fail)
        user2 = User(
            email="user2@example.com",
            hashed_password=hash_password("Test123!@#"),
            full_name="User 2",
            role=RoleEnum.user
        )
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user2)
        
        token2 = create_access_token({"sub": str(user2.id), "role": "user"})
        
        rsvp2_response = await client.post(
            "/api/v1/rsvps/",
            headers={"Authorization": f"Bearer {token2}"},
            json={"event_id": event["id"], "status": "going"}
        )
        
        assert rsvp2_response.status_code == 400
        assert "capacity" in rsvp2_response.json()["detail"].lower()
