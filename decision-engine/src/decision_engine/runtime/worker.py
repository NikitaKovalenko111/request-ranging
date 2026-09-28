from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
import logging
from typing import Any, Mapping

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import ConsumerRecord

from ..pipeline import DecisionPipeline, PipelineOrder
from ..rule_engine.domain import DomainValidationError, OrderStatus, OrderType
from ..rule_engine.rules_repository import RedisRuleRepository
from .config import RuntimeSettings
from .repository import RedisExecutorProfileRepository

logger = logging.getLogger(__name__)


class DecisionEngineWorker:
    def __init__(
        self,
        settings: RuntimeSettings,
        consumer: AIOKafkaConsumer,
        producer: AIOKafkaProducer,
        profiles: RedisExecutorProfileRepository,
        rules: RedisRuleRepository,
        pipeline: DecisionPipeline,
    ) -> None:
        self._settings = settings
        self._consumer = consumer
        self._producer = producer
        self._profiles = profiles
        self._rules = rules
        self._pipeline = pipeline

    async def run(self) -> None:
        async for record in self._consumer:
            try:
                await self._process(record)
            except (json.JSONDecodeError, UnicodeDecodeError, DomainValidationError, ValueError, TypeError, KeyError) as error:
                await self._send_dlq(record, error)
                await self._consumer.commit()
            except Exception:
                logger.exception(
                    "decision processing failed",
                    extra={
                        "topic": record.topic,
                        "partition": record.partition,
                        "offset": record.offset,
                    },
                )
                raise

    async def _process(self, record: ConsumerRecord) -> None:
        event = json.loads(record.value.decode("utf-8"))
        if not isinstance(event, Mapping):
            raise DomainValidationError("Kafka event must be a JSON object")
        event_type = str(event.get("event_type", ""))
        if event_type not in {"OrderCreated", "OrderUpdated"}:
            await self._consumer.commit()
            return

        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            raise DomainValidationError("event.payload must be an object")
        if str(payload.get("status", "")).lower() != OrderStatus.PROCESSED.value:
            await self._consumer.commit()
            return

        order = build_pipeline_order(event, payload)
        profiles = await self._profiles.list_active()
        # On a clean stack the backend may still be consuming the executor
        # startup snapshot when the first order arrives.
        for _ in range(10):
            if profiles:
                break
            await asyncio.sleep(0.5)
            profiles = await self._profiles.list_active()
        dynamic_rules = await self._rules.list_enabled()
        result = await self._pipeline.decide(order, profiles, dynamic_rules)
        await self._consumer.commit()
        logger.info(
            "decision published",
            extra={
                "order_id": order.id,
                "candidate_count": len(profiles),
                "eligible_count": len(result.rule_result.eligible_executor_ids),
                "selected_executor_id": result.selected_executor_id,
            },
        )

    async def _send_dlq(self, record: ConsumerRecord, error: Exception) -> None:
        value = json.dumps(
            {
                "event_type": "DecisionEngineInputRejected",
                "occurred_at": datetime.now(UTC).isoformat(),
                "source_topic": record.topic,
                "partition": record.partition,
                "offset": record.offset,
                "error": str(error),
                "payload": record.value.decode("utf-8", errors="replace"),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        await self._producer.send_and_wait(
            self._settings.kafka_dlq_topic,
            value,
            key=record.key,
        )


def build_pipeline_order(
    event: Mapping[str, Any], payload: Mapping[str, Any]
) -> PipelineOrder:
    attributes = payload.get("attributes")
    if not isinstance(attributes, Mapping):
        raise DomainValidationError("order attributes must be an object")
    occurred_at = str(event.get("occurred_at", "")).replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(occurred_at)
    except ValueError as error:
        raise DomainValidationError("occurred_at must be ISO-8601") from error
    if timestamp.tzinfo is None:
        raise DomainValidationError("occurred_at must include timezone")

    return PipelineOrder(
        id=str(payload["order_id"]),
        timestamp=timestamp,
        parent_id=payload.get("parent_id"),
        sum=int(attributes["sum"]),
        order_type=OrderType.parse(attributes["order_type"]),
        subject=str(attributes["subject"]),
        status=OrderStatus(str(payload["status"]).lower()),
        weight=float(payload["weight"]),
        client_msp=_optional_text(attributes.get("client_msp")),
        executor_msp=_optional_text(attributes.get("executor_msp")),
        vip=_boolean(attributes.get("vip", False)),
        text=_optional_text(attributes.get("text")),
    )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, "0", "false", "False"):
        return False
    if value in (1, "1", "true", "True"):
        return True
    raise DomainValidationError("vip must be boolean")

