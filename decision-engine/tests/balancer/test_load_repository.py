import asyncio
import json

import pytest
from redis.exceptions import ConnectionError

from decision_engine.balancer import LoadRepositoryError, RedisLoadRepository


class FakeRedis:
    def __init__(self, documents=None, error=None) -> None:
        self.documents = documents or []
        self.error = error
        self.calls = []

    async def mget(self, keys):
        self.calls.append(list(keys))
        if self.error is not None:
            raise self.error
        return self.documents


def test_redis_repository_uses_one_mget_and_defaults_missing_key() -> None:
    async def scenario() -> None:
        redis = FakeRedis(
            [
                json.dumps(
                    {
                        "active_count": 7,
                        "active_weight": 12.5,
                        "pending_count": 2,
                        "pending_weight": 4.0,
                        "processed_today": 38,
                        "last_assignment_at": "2026-09-27T10:30:00Z",
                    }
                ),
                None,
            ]
        )
        result = await RedisLoadRepository(redis).get_many(["executor-28", "missing"])

        assert redis.calls == [[
            "executor:load:executor-28",
            "executor:load:missing",
        ]]
        assert result["executor-28"].active_weight == 12.5
        assert result["executor-28"].pending_weight == 4.0
        assert result["missing"].active_weight == 0.0

    asyncio.run(scenario())


def test_redis_failure_becomes_explicit_repository_error() -> None:
    async def scenario() -> None:
        repository = RedisLoadRepository(FakeRedis(error=ConnectionError("down")))

        with pytest.raises(LoadRepositoryError, match="unavailable"):
            await repository.get_many(["A"])

    asyncio.run(scenario())


def test_invalid_runtime_json_fails_fast() -> None:
    async def scenario() -> None:
        repository = RedisLoadRepository(FakeRedis(["not-json"]))

        with pytest.raises(LoadRepositoryError, match="invalid runtime load"):
            await repository.get_many(["A"])

    asyncio.run(scenario())

