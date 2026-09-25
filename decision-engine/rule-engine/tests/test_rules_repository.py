import asyncio
import json

from executor_rule_engine.rules_repository import RedisRuleRepository


class FakeRedis:
    def __init__(self, document: str | None) -> None:
        self.document = document
        self.get_count = 0

    async def get(self, key: str) -> str | None:
        self.get_count += 1
        return self.document


def test_rules_repository_uses_short_lived_local_cache() -> None:
    async def scenario() -> None:
        redis = FakeRedis(
            json.dumps(
                [
                    {
                        "id": "rule-1",
                        "name": "Rule",
                        "condition": {
                            "code": "ALWAYS",
                            "left": {"source": "constant", "value": True},
                            "operator": "EQ",
                            "right": {"source": "constant", "value": True},
                        },
                    }
                ]
            )
        )
        repository = RedisRuleRepository(  # type: ignore[arg-type]
            redis, rules_key="rules:active", local_ttl_seconds=60
        )

        first = await repository.list_enabled()
        second = await repository.list_enabled()

        assert first is second
        assert redis.get_count == 1
        repository.invalidate()
        await repository.list_enabled()
        assert redis.get_count == 2

    asyncio.run(scenario())


def test_missing_rules_key_means_no_dynamic_rules() -> None:
    async def scenario() -> None:
        repository = RedisRuleRepository(  # type: ignore[arg-type]
            FakeRedis(None), local_ttl_seconds=60
        )

        assert await repository.list_enabled() == ()

    asyncio.run(scenario())
