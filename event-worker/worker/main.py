import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType

from .config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("event-worker")


async def handle_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)   # ← добавь json.loads
        log.info(
            "event received: event=%s tracking_no=%s status=%s",
            payload.get("event"),
            payload.get("tracking_no"),
            payload.get("status"),
        )


async def run() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        settings.exchange_name,
        ExchangeType.TOPIC,
        durable=True,
    )
    queue = await channel.declare_queue(settings.queue_name, durable=True, arguments={"x-queue-type": "quorum"} )
    await queue.bind(exchange, routing_key=settings.routing_key_status)

    log.info("worker started, queue=%s", settings.queue_name)

    await queue.consume(handle_message)

    try:
        await asyncio.Future()   # держим процесс живым
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run())