import asyncio
import json
from types import SimpleNamespace

import pytest

from decision_engine.publisher import KafkaDecisionResultPublisher


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bytes, bytes | None]] = []

    async def send_and_wait(
        self,
        topic: str,
        value: bytes,
        key: bytes | None = None,
    ) -> None:
        self.sent.append((topic, value, key))


def test_kafka_publisher_sends_final_event_with_order_key() -> None:
    async def scenario() -> None:
        producer = FakeProducer()
        publisher = KafkaDecisionResultPublisher(
            producer,
            topic='orders.decisions',
        )
        candidate = SimpleNamespace(
            as_dict=lambda: {
                'executor_id': '7',
                'rank': 1,
                'ml_score': 0.8,
                'effective_load': 0.0,
            }
        )
        result = SimpleNamespace(order_id=42, balanced_candidates=(candidate,))

        await publisher.publish(result)  # type: ignore[arg-type]

        assert len(producer.sent) == 1
        topic, value, key = producer.sent[0]
        event = json.loads(value)
        assert topic == 'orders.decisions'
        assert key == b'42'
        assert event['event_type'] == 'ExecutorDecisionCompleted'
        assert event['event_version'] == 1
        assert event['balanced_candidates'][0]['executor_id'] == '7'
        assert set(event) == {
            'event_type',
            'event_version',
            'occurred_at',
            'order_id',
            'balanced_candidates',
        }

    asyncio.run(scenario())


def test_kafka_publisher_propagates_delivery_error() -> None:
    class FailingProducer:
        async def send_and_wait(self, topic, value, key=None) -> None:
            raise RuntimeError('Kafka unavailable')

    async def scenario() -> None:
        publisher = KafkaDecisionResultPublisher(FailingProducer())
        result = SimpleNamespace(order_id=42, balanced_candidates=())
        with pytest.raises(RuntimeError, match='Kafka unavailable'):
            await publisher.publish(result)  # type: ignore[arg-type]

    asyncio.run(scenario())
