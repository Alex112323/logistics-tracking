import json

import aio_pika
from aio_pika import ExchangeType

from .config import settings

_connection: aio_pika.RobustConnection | None = None
_channel: aio_pika.abc.AbstractRobustChannel | None = None
_exchange: aio_pika.abc.AbstractRobustExchange | None = None


async def init_broker() -> None:
    global _connection, _channel, _exchange
    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    _channel = await _connection.channel()
    _exchange = await _channel.declare_exchange(
        settings.exchange_name,
        ExchangeType.TOPIC,
        durable=True,
    )


async def close_broker() -> None:
    if _connection is not None:
        await _connection.close()


async def publish_status_changed(payload: dict) -> None:
    if _exchange is None:
        raise RuntimeError("Broker exchange is not initialized")
    message = aio_pika.Message(
        body=json.dumps(payload, default=str).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await _exchange.publish(message, routing_key=settings.routing_key_status)