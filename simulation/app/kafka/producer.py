import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from aiokafka import AIOKafkaProducer
from ..config import settings
from ..models.event import EventEnvelope, get_current_rfc3339

logger = logging.getLogger("ais.kafka")


class KafkaPublishError(RuntimeError):
    """Raised when Kafka delivery fails while kafka_enabled=True."""
    pass


class KafkaEventProducer:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.is_connected = False
        self.in_memory_log: List[Dict[str, Any]] = []  # For debug and testing inspection

    async def start(self, retries: int = 15, initial_delay: float = 2.0):
        if not settings.kafka_enabled:
            logger.info("Kafka is disabled by configuration (KAFKA_ENABLED=false). Events will be logged to memory/console.")
            return

        delay = initial_delay
        for attempt in range(1, retries + 1):
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=settings.kafka_brokers,
                    key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
                    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                    request_timeout_ms=5000,
                )
                await self.producer.start()
                self.is_connected = True
                logger.info(f"Connected to Kafka brokers at {settings.kafka_brokers} (attempt {attempt}/{retries})")
                return
            except Exception as e:
                logger.warning(f"Kafka connection attempt {attempt}/{retries} to {settings.kafka_brokers} failed: {e}. Retrying in {delay:.1f}s...")
                if attempt < retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 10.0)
                else:
                    logger.error(f"Failed to connect to Kafka brokers at {settings.kafka_brokers} after {retries} attempts.")
                    self.producer = None
                    self.is_connected = False
                    raise KafkaPublishError(f"Cannot connect to Kafka brokers at {settings.kafka_brokers} after {retries} attempts: {e}") from e

    async def stop(self):
        if self.producer and self.is_connected:
            try:
                await self.producer.stop()
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
            finally:
                self.is_connected = False

    async def send_event(self, topic: str, key: str, envelope: EventEnvelope):
        data = envelope.model_dump()
        self.in_memory_log.append({"topic": topic, "key": key, "event": data})
        # Keep in_memory_log bounded to last 2000 events
        if len(self.in_memory_log) > 2000:
            self.in_memory_log.pop(0)

        if settings.kafka_enabled:
            if not self.is_connected or not self.producer:
                raise KafkaPublishError(f"Kafka is enabled but producer is not connected to {settings.kafka_brokers}")
            try:
                await self.producer.send_and_wait(topic, key=key, value=data)
            except Exception as e:
                logger.error(f"Failed to publish event {envelope.event_type} to {topic}: {e}")
                raise KafkaPublishError(f"Failed to publish event {envelope.event_type} to {topic}: {e}") from e
        else:
            logger.debug(f"[MOCK KAFKA] [{topic}] key={key} type={envelope.event_type}")

    async def send_batch(self, topic: str, batch: List[Tuple[str, EventEnvelope]]):
        """Batch send for burst mode efficiency."""
        for key, envelope in batch:
            self.in_memory_log.append({"topic": topic, "key": key, "event": envelope.model_dump()})
        if len(self.in_memory_log) > 2000:
            self.in_memory_log = self.in_memory_log[-2000:]

        if settings.kafka_enabled:
            if not self.is_connected or not self.producer:
                raise KafkaPublishError(f"Kafka is enabled but producer is not connected to {settings.kafka_brokers}")
            tasks = []
            for key, envelope in batch:
                data = envelope.model_dump()
                tasks.append(self.producer.send(topic, key=key, value=data))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"Failed to publish batch to {topic}: {r}")
                    raise KafkaPublishError(f"Failed to publish batch to {topic}: {r}") from r
        else:
            logger.debug(f"[MOCK KAFKA] [{topic}] batch size={len(batch)}")

    async def publish_order_created(self, order_dict: Dict[str, Any]):
        payload = {
            "order_id": order_dict["order_id"],
            "parent_id": order_dict.get("parent_id"),
            "status": order_dict["status"],
            "weight": order_dict["weight"],
            "version": order_dict.get("version", 1),
            "attributes": order_dict["attributes"],
        }
        envelope = EventEnvelope(
            event_type="OrderCreated",
            event_version=1,
            occurred_at=get_current_rfc3339(),
            payload=payload,
        )
        await self.send_event(settings.order_topic, key=order_dict["order_id"], envelope=envelope)

    async def publish_order_updated(self, order_dict: Dict[str, Any]):
        payload = {
            "order_id": order_dict["order_id"],
            "parent_id": order_dict.get("parent_id"),
            "status": order_dict["status"],
            "weight": order_dict["weight"],
            "version": order_dict["version"],
            "attributes": order_dict["attributes"],
        }
        envelope = EventEnvelope(
            event_type="OrderUpdated",
            event_version=1,
            occurred_at=get_current_rfc3339(),
            payload=payload,
        )
        await self.send_event(settings.order_topic, key=order_dict["order_id"], envelope=envelope)

    async def publish_order_status_changed(
        self,
        order_id: str,
        previous_status: str,
        status: str,
        version: int,
    ):
        payload = {
            "order_id": order_id,
            "previous_status": previous_status,
            "status": status,
            "version": version,
        }
        envelope = EventEnvelope(
            event_type="OrderStatusChanged",
            event_version=1,
            occurred_at=get_current_rfc3339(),
            payload=payload,
        )
        await self.send_event(settings.order_topic, key=order_id, envelope=envelope)

    async def publish_executor_created(self, executor_dict: Dict[str, Any]):
        payload = {
            "executor_id": executor_dict["executor_id"],
            "active": executor_dict["active"],
            "capacity": executor_dict["capacity"],
            "daily_limit": executor_dict.get("daily_limit"),
            "version": executor_dict.get("version", 1),
            "skills": executor_dict.get("skills", []),
            "attributes": executor_dict["attributes"],
        }
        envelope = EventEnvelope(
            event_type="ExecutorCreated",
            event_version=1,
            occurred_at=get_current_rfc3339(),
            payload=payload,
        )
        await self.send_event(settings.executor_topic, key=executor_dict["executor_id"], envelope=envelope)

    async def publish_executor_updated(self, executor_dict: Dict[str, Any]):
        payload = {
            "executor_id": executor_dict["executor_id"],
            "active": executor_dict["active"],
            "capacity": executor_dict["capacity"],
            "daily_limit": executor_dict.get("daily_limit"),
            "version": executor_dict["version"],
            "skills": executor_dict.get("skills", []),
            "attributes": executor_dict["attributes"],
        }
        envelope = EventEnvelope(
            event_type="ExecutorUpdated",
            event_version=1,
            occurred_at=get_current_rfc3339(),
            payload=payload,
        )
        await self.send_event(settings.executor_topic, key=executor_dict["executor_id"], envelope=envelope)


kafka_producer = KafkaEventProducer()
