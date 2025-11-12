import asyncio, json
from aio_pika import connect_robust, ExchangeType
from app.core.config import settings
from app.core.logging import logger
from app.websocket.manager import manager
from app.db.session import AsyncSessionLocal
from app.db.models import Event, RSVP, User
from sqlalchemy import select

async def handle_message(body: bytes):
    data = json.loads(body.decode())
    typ = data.get("type")
    if typ == "rsvp.created":
        # push notification to event creator and user
        event_id = data.get("event_id")
        user_id = data.get("user_id")
        # fetch some data for message
        async with AsyncSessionLocal() as session:
            ev = (await session.execute(select(Event).where(Event.id == event_id))).scalars().first()
            usr = (await session.execute(select(User).where(User.id == user_id))).scalars().first()
            if ev:
                payload = {"type": "rsvp.created", "event_id": str(event_id), "event_title": ev.title, "user_email": usr.email if usr else None}
                # send to creator
                await manager.send_personal_message(ev.created_by, payload)
                # optionally send to rsvp user as confirmation
                await manager.send_personal_message(user_id, {"type":"rsvp.confirmation","event":ev.title})
    # handle other event types here

async def run_worker():
    max_retries = 10
    delay = 5  # seconds
    for attempt in range(1, max_retries + 1):
        try:
            connection = await connect_robust(settings.RABBITMQ_URL)
            logger.info("Successfully connected to RabbitMQ")
            break
        except Exception as e:
            logger.error(f"RabbitMQ connection failed (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise
            await asyncio.sleep(delay)
    channel = await connection.channel()
    exchange = await channel.declare_exchange("communityhub.events", ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue("communityhub.notifications", durable=True)
    await queue.bind(exchange, routing_key="rsvp.*")
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    await handle_message(message.body)
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
