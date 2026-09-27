from __future__ import annotations

import json
from typing import Protocol, Sequence

from redis.asyncio import Redis
from redis.exceptions import RedisError

from .schemas import BalancerValidationError, ExecutorLoad


class LoadRepositoryError(RuntimeError):
    """Runtime load storage is unavailable or returned unusable data."""


class LoadRepository(Protocol):
    async def get_many(self, executor_ids: list[str]) -> dict[str, ExecutorLoad]: ...


class RedisLoadRepository:
    """Read-only JSON adapter using one Redis MGET for the whole candidate set."""

    def __init__(
        self,
        redis: Redis,
        *,
        key_prefix: str = "executor:load:",
    ) -> None:
        self._redis = redis
        self._key_prefix = key_prefix

    async def get_many(self, executor_ids: list[str]) -> dict[str, ExecutorLoad]:
        unique_ids = list(dict.fromkeys(executor_ids))
        if not unique_ids:
            return {}
        keys = [f"{self._key_prefix}{executor_id}" for executor_id in unique_ids]
        try:
            documents = await self._redis.mget(keys)
        except RedisError as error:
            raise LoadRepositoryError("Redis runtime load is unavailable") from error

        result: dict[str, ExecutorLoad] = {}
        for executor_id, document in zip(unique_ids, documents, strict=True):
            if document is None:
                result[executor_id] = ExecutorLoad()
                continue
            try:
                payload = json.loads(document)
                if not isinstance(payload, dict):
                    raise TypeError("runtime load JSON must be an object")
                result[executor_id] = ExecutorLoad.from_mapping(payload)
            except (json.JSONDecodeError, TypeError, ValueError, BalancerValidationError) as error:
                raise LoadRepositoryError(
                    f"invalid runtime load for executor {executor_id}"
                ) from error
        return result


class InMemoryLoadRepository:
    """Small deterministic repository for local use and tests."""

    def __init__(self, loads: dict[str, ExecutorLoad] | None = None) -> None:
        self._loads = dict(loads or {})

    async def get_many(self, executor_ids: list[str]) -> dict[str, ExecutorLoad]:
        return {
            executor_id: self._loads.get(executor_id, ExecutorLoad())
            for executor_id in dict.fromkeys(executor_ids)
        }

