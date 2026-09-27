from __future__ import annotations

from datetime import UTC, datetime
import json
from math import isfinite
import os
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .pipeline import PipelineResult


class DecisionResultPublisher(Protocol):
    async def publish(self, result: PipelineResult) -> None: ...


class KafkaProducer(Protocol):
    async def send_and_wait(
        self,
        topic: str,
        value: bytes,
        key: bytes | None = None,
    ) -> Any: ...


def build_decision_event(
    result: PipelineResult,
    *,
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        'event_type': 'ExecutorDecisionCompleted',
        'event_version': 1,
        'occurred_at': (occurred_at or datetime.now(UTC)).isoformat(),
        'order_id': result.order_id,
        'balanced_candidates': _json_safe(
            [candidate.as_dict() for candidate in result.balanced_candidates]
        ),
    }


class KafkaDecisionResultPublisher:
    '''Publishes one final event after all decision stages have completed.'''

    def __init__(
        self,
        producer: KafkaProducer,
        *,
        topic: str = 'orders.decision-engine.completed',
    ) -> None:
        if not topic.strip():
            raise ValueError('Kafka result topic cannot be empty')
        self._producer = producer
        self._topic = topic

    @classmethod
    def from_env(cls, producer: KafkaProducer) -> KafkaDecisionResultPublisher:
        return cls(
            producer,
            topic=os.getenv(
                'KAFKA_DECISION_RESULT_TOPIC',
                'orders.decision-engine.completed',
            ),
        )

    async def publish(self, result: PipelineResult) -> None:
        event = build_decision_event(result)
        value = json.dumps(
            event,
            ensure_ascii=False,
            allow_nan=False,
            separators=(',', ':'),
        ).encode('utf-8')
        await self._producer.send_and_wait(
            self._topic,
            value,
            key=str(result.order_id).encode('utf-8'),
        )


class InMemoryDecisionResultPublisher:
    '''Deterministic publisher for local runs and tests.'''

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(self, result: PipelineResult) -> None:
        self.events.append(build_decision_event(result))


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
