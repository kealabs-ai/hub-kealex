"""Standalone RabbitMQ worker for access decision audit events."""
import asyncio
import json
import logging
import os

import aio_pika

logger = logging.getLogger("kealex.access.audit")
QUEUE_NAME = "kealex.access.audit"


async def _consume(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        try:
            event = json.loads(message.body)
            logger.info(
                "tenant_access decision=%s tenant_id=%s user_id=%s event_id=%s",
                event.get("decision"),
                event.get("tenant_id"),
                event.get("user_id"),
                event.get("event_id"),
            )
        except (ValueError, TypeError):
            logger.warning("Discarding malformed tenant access audit event")


async def main() -> None:
    connection = await aio_pika.connect_robust(
        host=os.environ["KEALEX_RABBITMQ_HOST"],
        port=int(os.getenv("KEALEX_RABBITMQ_PORT", "5672")),
        login=os.environ["KEALEX_RABBITMQ_USER"],
        password=os.environ["KEALEX_RABBITMQ_PASSWORD"],
        virtualhost=os.getenv("KEALEX_RABBITMQ_VHOST", "/"),
    )
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=100)
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.consume(_consume, no_ack=False)
        logger.info("Access audit worker listening on %s", QUEUE_NAME)
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("KEALEX_LOG_LEVEL", "INFO"))
    asyncio.run(main())
