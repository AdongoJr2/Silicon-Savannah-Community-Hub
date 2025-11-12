import json
import asyncio
from aio_pika import connect_robust, Message, ExchangeType
from app.core.config import settings

_connection = None
_channel = None

async def get_rabbit_connection():
    global _connection, _channel
    if _connection and not _connection.is_closed:
        return _connection, _channel
    _connection = await connect_robust(settings.RABBITMQ_URL)
    _channel = await _connection.channel()
    return _connection, _channel

async def publish_event(routing_key: str, payload: dict):
    _, channel = await get_rabbit_connection()
    exchange = await channel.declare_exchange("communityhub.events", ExchangeType.TOPIC, durable=True)
    body = json.dumps(payload).encode()
    message = Message(body, content_type="application/json")
    await exchange.publish(message, routing_key=routing_key)
