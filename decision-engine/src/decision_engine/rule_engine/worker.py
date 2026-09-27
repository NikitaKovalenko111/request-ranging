from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import ConsumerRecord

from .config import Settings
from .domain import DomainValidationError, Order
from .engine import RuleEngine
from .redis_repository import RedisExecutorRepository
from .rules_repository import RedisRuleRepository

logger = logging.getLogger(__name__)


class RuleEngineWorker:
    def __init__(
        self,
        settings: Settings,
        consumer: AIOKafkaConsumer,
        producer: AIOKafkaProducer,
        repository: RedisExecutorRepository,
        rule_repository: RedisRuleRepository,
        engine: RuleEngine,
    ) -> None:
        self._settings = settings
        self._consumer = consumer
        self._producer = producer
        self._repository = repository
        self._rule_repository = rule_repository
        self._engine = engine

    async def run(self) -> None:
        async for record in self._consumer:
            try:
                await self._process(record)
            except (json.JSONDecodeError, UnicodeDecodeError, DomainValidationError) as error:
                await self._send_dlq(record, error)
                await self._consumer.commit()
            except Exception:
                # Offset is deliberately not committed: Kafka will redeliver the
                # event after restart/rebalance instead of silently losing it.
                logger.exception(
                    "order processing failed",
                    extra={"topic": record.topic, "partition": record.partition, "offset": record.offset},
                )
                raise

    async def _process(self, record: ConsumerRecord) -> None:
        payload = json.loads(record.value.decode("utf-8"))
        if not isinstance(payload, dict):
            raise DomainValidationError("Kafka payload must be a JSON object")

        order_payload = payload.get("order", payload)
        if not isinstance(order_payload, dict):
            raise DomainValidationError("order must be a JSON object")

        order = Order.from_dict(order_payload)
        executors = await self._repository.list_online()
        dynamic_rules = await self._rule_repository.list_enabled()
        result = self._engine.filter(order, executors, dynamic_rules)

        event_id = str(
            payload.get("event_id")
            or f"{record.topic}:{record.partition}:{record.offset}"
        )
        output: dict[str, Any] = {
            "event_id": event_id,
            "event_type": "OrderCandidatesFiltered",
            "occurred_at": datetime.now(UTC).isoformat(),
            **result.as_dict(),
        }
        output["traces"] = [decision.trace_dict() for decision in result.decisions]
        await self._producer.send_and_wait(
            self._settings.kafka_result_topic,
            json.dumps(output, ensure_ascii=False).encode("utf-8"),
            key=str(order.id).encode("utf-8"),
        )
        await self._consumer.commit()
        logger.info(
            "order filtered",
            extra={
                "order_id": order.id,
                "candidate_count": len(executors),
                "eligible_count": len(result.eligible_executor_ids),
            },
        )

    async def _send_dlq(self, record: ConsumerRecord, error: Exception) -> None:
        output = {
            "event_type": "RuleEngineInputRejected",
            "occurred_at": datetime.now(UTC).isoformat(),
            "source": {
                "topic": record.topic,
                "partition": record.partition,
                "offset": record.offset,
            },
            "error": str(error),
            "payload": record.value.decode("utf-8", errors="replace"),
        }
        await self._producer.send_and_wait(
            self._settings.kafka_dlq_topic,
            json.dumps(output, ensure_ascii=False).encode("utf-8"),
            key=record.key,
        )
        logger.warning("invalid order sent to DLQ", extra=output["source"])
