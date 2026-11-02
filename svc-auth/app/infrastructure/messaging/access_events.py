"""Best-effort asynchronous tenant access audit events via RabbitMQ."""
import json
import asyncio
import logging
import os
import threading
from datetime import datetime, timezone
from uuid import uuid4
from prometheus_client import Counter

logger = logging.getLogger(__name__)
_lock = threading.Lock()
ACCESS_DECISIONS = Counter("kealex_tenant_access_decisions_total", "Tenant access decisions", ["decision"])


class _DeferredPublisher:
    """Queue events until the async RabbitMQ publisher is connected."""

    def __init__(self):
        self._pending = []
        self._loop = None
        self._connection = None
        self._channel = None

    def delay(self, *, tenant_id, user_id, decision):
        if not tenant_id:
            return
        ACCESS_DECISIONS.labels(decision=decision).inc()
        event = {
            "event_id": str(uuid4()), "tenant_id": str(tenant_id),
            "user_id": str(user_id) if user_id else None, "decision": decision,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
        with _lock:
            if len(self._pending) >= 1000:
                self._pending.pop(0)
            self._pending.append(event)
            loop = self._loop
        if loop and loop.is_running():
            import asyncio
            asyncio.run_coroutine_threadsafe(self._flush(), loop)

    async def connect(self):
        host = os.getenv("KEALEX_RABBITMQ_HOST")
        if not host:
            return
        import aio_pika
        self._loop = asyncio.get_running_loop()
        try:
            self._connection = await aio_pika.connect_robust(
                host=host, port=int(os.getenv("KEALEX_RABBITMQ_PORT", "5672")),
                login=os.getenv("KEALEX_RABBITMQ_USER", "kealex"),
                password=os.getenv("KEALEX_RABBITMQ_PASSWORD", ""),
                virtualhost=os.getenv("KEALEX_RABBITMQ_VHOST", "/"),
            )
            self._channel = await self._connection.channel()
            queue = await self._channel.declare_queue("kealex.access.audit", durable=True)
            await queue.consume(self._consume, no_ack=False)
            await self._flush()
        except Exception:
            logger.exception("RabbitMQ access audit unavailable")

    async def close(self):
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def _consume(self, message):
        async with message.process():
            try:
                event = json.loads(message.body)
                logger.info("tenant_access decision=%s tenant_id=%s user_id=%s event_id=%s",
                            event.get("decision"), event.get("tenant_id"),
                            event.get("user_id"), event.get("event_id"))
            except (ValueError, TypeError):
                logger.warning("Discarding malformed tenant access audit event")

    async def _flush(self):
        if not self._channel:
            return
        import aio_pika
        while True:
            with _lock:
                if not self._pending:
                    return
                event = self._pending.pop(0)
            try:
                await self._channel.default_exchange.publish(
                    aio_pika.Message(json.dumps(event).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                                     content_type="application/json"),
                    routing_key="kealex.access.audit",
                )
            except Exception:
                with _lock:
                    self._pending.insert(0, event)
                logger.exception("Could not publish access audit event")
                return


publish_access_event = _DeferredPublisher()
