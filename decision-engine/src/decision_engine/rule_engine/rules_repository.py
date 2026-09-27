from __future__ import annotations

import asyncio
import json
from time import monotonic

from redis.asyncio import Redis

from .dynamic_rules import DistributionRule, RuleConfigurationError, parse_rules


class RedisRuleRepository:
    """Reads the dynamic rule set prepared by backend from a Redis cache."""

    def __init__(
        self,
        redis: Redis,
        *,
        rules_key: str = "rules:active",
        local_ttl_seconds: float = 5.0,
    ) -> None:
        self._redis = redis
        self._rules_key = rules_key
        self._local_ttl_seconds = max(0.0, local_ttl_seconds)
        self._cached: tuple[DistributionRule, ...] | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def list_enabled(self) -> tuple[DistributionRule, ...]:
        now = monotonic()
        if self._cached is not None and now < self._expires_at:
            return self._cached

        async with self._lock:
            now = monotonic()
            if self._cached is not None and now < self._expires_at:
                return self._cached

            document = await self._redis.get(self._rules_key)
            if document is None:
                rules: tuple[DistributionRule, ...] = ()
            else:
                try:
                    rules = parse_rules(json.loads(document))
                except json.JSONDecodeError as error:
                    raise RuleConfigurationError("rules cache contains invalid JSON") from error

            self._cached = rules
            self._expires_at = now + self._local_ttl_seconds
            return rules

    def invalidate(self) -> None:
        """Allows a future cache-invalidation consumer to force the next reload."""
        self._expires_at = 0.0

