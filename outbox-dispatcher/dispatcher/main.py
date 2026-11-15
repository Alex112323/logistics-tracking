import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType

from . import db
from .config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("outbox-dispatcher")


async def run() -> None:
    await db.init_pool()

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        settings.exchange_name, ExchangeType.TOPIC, durable=True
    )

    log.info("dispatcher started, poll=%sms", settings.poll_interval_ms)

    try:
        while True:
            rows = await db.fetch_unpublished(settings.batch_size)
            if not rows:
                await asyncio.sleep(settings.poll_interval_ms / 1000)
                continue

            published_ids: list[int] = []
            for row in rows:
                try:
                    message = aio_pika.Message(
                        body=json.dumps(row["payload"], default=str).encode(),
                        content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    )
                    await exchange.publish(message, routing_key=row["event_type"])
                    published_ids.append(row["id"])
                except Exception:
                    log.exception("publish failed for outbox id=%s", row["id"])
                    break

            if published_ids:
                await db.mark_published(published_ids)
                log.info("published %d outbox rows", len(published_ids))
    finally:
        await connection.close()
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(run())