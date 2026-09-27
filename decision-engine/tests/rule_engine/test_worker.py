import asyncio
import json
from types import SimpleNamespace
from uuid import UUID

from decision_engine.rule_engine.config import Settings
from decision_engine.rule_engine.domain import Executor, ExecutorSettings, OrderType
from decision_engine.rule_engine.engine import default_rule_engine
from decision_engine.rule_engine.worker import RuleEngineWorker


class FakeConsumer:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class FakeProducer:
    def __init__(self) -> None:
        self.sent = []

    async def send_and_wait(self, topic, value, key=None) -> None:
        self.sent.append((topic, value, key))


class FakeRepository:
    async def list_online(self):
        return [
            Executor(
                user_id=101,
                active=True,
                daily_count=1,
                settings=ExecutorSettings(
                    order_type=OrderType.ORDER_1,
                    subject=UUID("96bc9564-fb0b-4db5-b4b6-ce11c2fb5e6f"),
                    max_daily_limit=10,
                ),
            )
        ]


class FakeRuleRepository:
    async def list_enabled(self):
        return ()


def test_worker_publishes_result_before_committing_offset() -> None:
    async def scenario() -> None:
        consumer = FakeConsumer()
        producer = FakeProducer()
        settings = Settings.from_env()
        worker = RuleEngineWorker(
            settings,
            consumer,  # type: ignore[arg-type]
            producer,  # type: ignore[arg-type]
            FakeRepository(),  # type: ignore[arg-type]
            FakeRuleRepository(),  # type: ignore[arg-type]
            default_rule_engine(),
        )
        payload = {
            "event_id": "event-1",
            "order": {
                "id": 42,
                "sum": 1_000,
                "order_type": "ORDER_1",
                "subject": "96bc9564-fb0b-4db5-b4b6-ce11c2fb5e6f",
                "status": "processed",
            },
        }
        record = SimpleNamespace(
            topic="orders.created",
            partition=0,
            offset=15,
            key=b"42",
            value=json.dumps(payload).encode(),
        )

        await worker._process(record)  # type: ignore[arg-type]

        assert consumer.commit_count == 1
        assert len(producer.sent) == 1
        topic, value, key = producer.sent[0]
        result = json.loads(value)
        assert topic == settings.kafka_result_topic
        assert key == b"42"
        assert result["event_id"] == "event-1"
        assert result["eligible_executor_ids"] == [101]

    asyncio.run(scenario())
