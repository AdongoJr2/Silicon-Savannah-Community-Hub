import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query, status, APIRouter
from app.api.v1.routes import auth as auth_router, events as events_router, rsvps as rsvps_router, health as health_router
from app.db.session import engine, Base
from app.events.consumer import run_worker
from app.websocket.manager import manager
from app.core.config import settings
from app.core.security import decode_token
from app.core.logging import logger
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import sqlalchemy

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="CommunityHub")

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router.router)
api_router.include_router(events_router.router)
api_router.include_router(rsvps_router.router)
api_router.include_router(health_router.router)

app.include_router(api_router)

@app.on_event("startup")
async def on_startup():
    # create tables (simple approach for demo)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # start background consumer in a task (worker is separate but for demo we also start here)
    # Note: In docker-compose, worker service runs the worker. Starting here helps local simple runs.
    asyncio.create_task(run_worker())

@app.websocket("/ws/notifications/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str = Query(...)):
    """
    WebSocket endpoint with JWT authentication.
    Clients must provide a valid access token as a query parameter.
    Example: ws://localhost:8000/ws/notifications/{user_id}?token=your_jwt_token
    """
    try:
        # Validate JWT token before accepting connection
        payload = decode_token(token)
        
        # Verify token type is 'access'
        if payload.get("type") != "access":
            logger.warning(f"WebSocket connection attempt with invalid token type for user {user_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Verify the token's user_id matches the websocket path parameter
        token_user_id = str(payload.get("sub"))
        if token_user_id != user_id:
            logger.warning(f"WebSocket connection attempt: token user_id {token_user_id} does not match path user_id {user_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Authentication successful - accept connection
        await manager.connect(user_id, websocket)
        logger.info(f"WebSocket connection established for user {user_id}")
        
        while True:
            # Keep the connection open, though we don't expect messages from client
            data = await websocket.receive_text()
            
    except ValueError as e:
        # Token validation failed
        logger.warning(f"WebSocket connection rejected for user {user_id}: {str(e)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        try:
            await manager.disconnect(user_id, websocket)
        except Exception:
            pass