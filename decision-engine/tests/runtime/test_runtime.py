from datetime import UTC
import json

import pytest

from decision_engine.balancer import RedisHashLoadRepository
from decision_engine.rule_engine.engine import integration_rule_engine
from decision_engine.runtime.repository import RedisExecutorProfileRepository
from decision_engine.runtime.worker import build_pipeline_order


class FakePipeline:
    def __init__(self, documents):
        self.documents = documents

    def hgetall(self, key):
        return self

    async def execute(self):
        return self.documents


class FakeRedis:
    def __init__(self, documents):
        self.documents = documents

    async def smembers(self, key):
        return {"executor-01"}

    def pipeline(self, transaction=False):
        return FakePipeline(self.documents)


def order_event():
    return {
        "event_type": "OrderCreated",
        "occurred_at": "2026-09-27T10:00:00Z",
        "payload": {
            "order_id": "order-1",
            "parent_id": None,
            "status": "processed",
            "weight": 1.0,
            "attributes": {
                "sum": 100000,
                "order_type": "LEGAL_REVIEW",
                "subject": "contract",
                "vip": False,
                "client_msp": "small",
                "executor_msp": "legal",
                "text": "Проверка договора поставки",
            },
        },
    }


@pytest.mark.asyncio
async def test_backend_redis_hash_builds_full_pipeline_profile():
    document = {
        "active": "1",
        "capacity": "2",
        "current_load": "0.5",
        "active_count": "1",
        "pending_count": "0",
        "processed_today": "4",
        "last_assignment_at": "2026-09-27T09:00:00Z",
        "skills": json.dumps(["ContractLaw", "Negotiations"]),
        "attributes": json.dumps(
            {
                "min_accept_sum": 0,
                "max_accept_sum": 500000,
                "client_msp": ["small", "medium"],
                "executor_msp": ["legal"],
                "order_types": ["LEGAL_REVIEW"],
                "subjects": ["contract"],
                "vip_allowed": True,
            }
        ),
    }
    redis = FakeRedis([document])
    profiles = await RedisExecutorProfileRepository(redis).list_active()
    loads = await RedisHashLoadRepository(redis).get_many(["executor-01"])

    assert profiles[0].user_id == "executor-01"
    assert profiles[0].settings.order_types[0].value == "LEGAL_REVIEW"
    assert profiles[0].skills == ("ContractLaw", "Negotiations")
    assert loads["executor-01"].active_weight == 0.5
    assert loads["executor-01"].last_assignment_at.tzinfo == UTC


def test_ais_event_and_executor_attributes_pass_integration_rules():
    event = order_event()
    order = build_pipeline_order(event, event["payload"])
    settings = {
        "order_types": ["LEGAL_REVIEW"],
        "subjects": ["contract"],
        "client_msp": ["small"],
        "executor_msp": ["legal"],
        "vip_allowed": True,
        "min_accept_sum": 0,
        "max_accept_sum": 500000,
    }
    from decision_engine.rule_engine.domain import Executor, ExecutorSettings

    result = integration_rule_engine().filter(
        order.as_rule_order(),
        [Executor("executor-01", ExecutorSettings.from_dict(settings))],
    )
    assert result.eligible_executor_ids == ["executor-01"]
