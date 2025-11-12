"""
Pytest configuration and fixtures for testing.
"""
import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.session import Base, get_session
from app.core.config import settings
from app.core.security import hash_password, create_access_token
from app.db.models.user import User, RoleEnum
from app.db.models.event import Event
from app.db.models.rsvp import RSVP, RSVPStatusEnum
from app.cache.redis_client import cache
import uuid
from datetime import datetime, timedelta


# Test database URL - use environment variable if available (for Docker)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/communityhub_test"
)

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,  # Disable connection pooling for tests
    echo=False,
)


# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.
    Automatically rolls back changes after test completion.
    """
    # Drop all tables first to ensure clean state
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a new session for the test
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit successful test changes
        except Exception:
            await session.rollback()  # Rollback on failure
            raise
        finally:
            await session.close()
    
    # Drop tables after test for complete isolation
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing API endpoints.
    Overrides the database session dependency.
    """
    async def override_get_session():
        yield db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with 'user' role."""
    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("Test123!@#"),
        full_name="Test User",
        role=RoleEnum.user
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_organizer(db_session: AsyncSession) -> User:
    """Create a test user with 'organizer' role."""
    user = User(
        email="organizer@example.com",
        hashed_password=hash_password("Test123!@#"),
        full_name="Test Organizer",
        role=RoleEnum.organizer
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test user with 'admin' role."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("Test123!@#"),
        full_name="Test Admin",
        role=RoleEnum.admin
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    """Generate a valid access token for test_user."""
    return create_access_token({"sub": str(test_user.id), "role": test_user.role.value})


@pytest.fixture
def organizer_token(test_organizer: User) -> str:
    """Generate a valid access token for test_organizer."""
    return create_access_token({"sub": str(test_organizer.id), "role": test_organizer.role.value})


@pytest.fixture
def admin_token(test_admin: User) -> str:
    """Generate a valid access token for test_admin."""
    return create_access_token({"sub": str(test_admin.id), "role": test_admin.role.value})


@pytest_asyncio.fixture
async def test_event(db_session: AsyncSession, test_organizer: User) -> Event:
    """Create a test event."""
    event = Event(
        title="Test Event",
        description="A test event description",
        location="Test Location",
        starts_at=datetime.utcnow() + timedelta(days=7),
        capacity=50,
        created_by=test_organizer.id
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def test_events(db_session: AsyncSession, test_organizer: User) -> list:
    """Create multiple test events."""
    events = []
    for i in range(5):
        event = Event(
            title=f"Event {i+1}",
            description=f"Description for event {i+1}",
            location=f"Location {i+1}",
            starts_at=datetime.utcnow() + timedelta(days=i+1),
            capacity=10 * (i+1),
            created_by=test_organizer.id
        )
        db_session.add(event)
        events.append(event)
    
    await db_session.commit()
    for event in events:
        await db_session.refresh(event)
    return events


@pytest_asyncio.fixture
async def test_rsvp(db_session: AsyncSession, test_user: User, test_event: Event) -> RSVP:
    """Create a test RSVP."""
    rsvp = RSVP(
        user_id=test_user.id,
        event_id=test_event.id,
        status=RSVPStatusEnum.going
    )
    db_session.add(rsvp)
    await db_session.commit()
    await db_session.refresh(rsvp)
    return rsvp


@pytest_asyncio.fixture(autouse=True)
async def clear_redis_cache():
    """Clear Redis cache before each test."""
    try:
        # Clear cache before test
        await cache.delete_pattern("*")
    except Exception:
        pass  # Redis might not be available in test environment
    yield
    # Don't clear after - let the cache state persist for the test to verify


@pytest.fixture(autouse=True)
def mock_password_hashing(monkeypatch):
    """
    Mock bcrypt password hashing for testing environments where bcrypt cannot be installed.
    This fixture is autouse, so it applies to all tests automatically.
    """
    class MockPasswordContext:
        """Mock password context that doesn't require bcrypt."""
        def hash(self, password: str) -> str:
            """Mock hash that just prefixes the password."""
            return f"$2b$12$mockedhash{password}"
        
        def verify(self, plain: str, hashed: str) -> bool:
            """Mock verify that checks if hash matches expected format."""
            expected_hash = f"$2b$12$mockedhash{plain}"
            return hashed == expected_hash
    
    # Patch the pwd_context in security module
    from app.core import security
    monkeypatch.setattr(security, "pwd_context", MockPasswordContext())


@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch):
    """Disable rate limiting for all tests."""
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    
    # Create a mock limiter that does nothing
    class MockLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    
    # Patch the limiter in all route modules
    import app.api.v1.routes.auth as auth_routes
    monkeypatch.setattr(auth_routes, "limiter", MockLimiter())


@pytest.fixture
def mock_publish_event(monkeypatch):
    """Mock the event publishing function to prevent RabbitMQ calls in tests."""
    async def mock_publish(*args, **kwargs):
        pass
    
    from app.events import publisher
    monkeypatch.setattr(publisher, "publish_event", mock_publish)
