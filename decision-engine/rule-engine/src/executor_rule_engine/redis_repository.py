from __future__ import annotations

import json
import logging

from redis.asyncio import Redis

from .domain import DomainValidationError, Executor

logger = logging.getLogger(__name__)


class RedisExecutorRepository:
    """Reads online executor snapshots without requiring the RedisJSON module."""

    def __init__(
        self,
        redis: Redis,
        *,
        online_set_key: str = "executors:online",
        executor_key_prefix: str = "executor:",
    ) -> None:
        self._redis = redis
        self._online_set_key = online_set_key
        self._executor_key_prefix = executor_key_prefix

    async def list_online(self) -> list[Executor]:
        executor_ids = sorted(await self._redis.smembers(self._online_set_key))
        if not executor_ids:
            return []

        keys = [f"{self._executor_key_prefix}{executor_id}" for executor_id in executor_ids]
        documents = await self._redis.mget(keys)
        executors: list[Executor] = []

        for executor_id, document in zip(executor_ids, documents, strict=True):
            if document is None:
                logger.warning("executor snapshot is missing", extra={"executor_id": executor_id})
                continue
            try:
                data = json.loads(document)
                executors.append(
                    Executor.from_dict(data, fallback_user_id=int(executor_id))
                )
            except (json.JSONDecodeError, DomainValidationError, TypeError, ValueError):
                logger.exception(
                    "invalid executor snapshot skipped", extra={"executor_id": executor_id}
                )

        return executors

