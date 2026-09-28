from __future__ import annotations

import json
from math import isfinite
from typing import Any, Mapping

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..pipeline import ExecutorProfile
from ..rule_engine.domain import DomainValidationError, ExecutorSettings


class ExecutorProfileRepositoryError(RuntimeError):
    pass


class RedisExecutorProfileRepository:
    """Builds pipeline profiles from hashes owned by the Go backend."""

    def __init__(
        self,
        redis: Redis,
        *,
        active_set_key: str = "executors:active",
        executor_key_prefix: str = "executor:",
    ) -> None:
        self._redis = redis
        self._active_set_key = active_set_key
        self._executor_key_prefix = executor_key_prefix

    async def list_active(self) -> list[ExecutorProfile]:
        try:
            executor_ids = sorted(await self._redis.smembers(self._active_set_key))
            if not executor_ids:
                return []
            pipeline = self._redis.pipeline(transaction=False)
            for executor_id in executor_ids:
                pipeline.hgetall(f"{self._executor_key_prefix}{executor_id}")
            documents = await pipeline.execute()
        except RedisError as error:
            raise ExecutorProfileRepositoryError(
                "Redis executor profiles are unavailable"
            ) from error

        profiles = []
        capacities = [
            _positive_float(document.get("capacity"), 1.0)
            for document in documents
            if document
        ]
        max_capacity = max(capacities, default=1.0)
        for executor_id, document in zip(executor_ids, documents, strict=True):
            if not document:
                continue
            try:
                profiles.append(
                    _profile_from_hash(
                        str(executor_id), document, max_capacity=max_capacity
                    )
                )
            except (ValueError, TypeError, json.JSONDecodeError, DomainValidationError) as error:
                raise ExecutorProfileRepositoryError(
                    f"invalid Redis profile for executor {executor_id}"
                ) from error
        return profiles


def _profile_from_hash(
    executor_id: str,
    document: Mapping[str, Any],
    *,
    max_capacity: float,
) -> ExecutorProfile:
    attributes = _json_object(document.get("attributes"), "attributes")
    skills = _json_strings(document.get("skills"), "skills")
    capacity = _positive_float(document.get("capacity"), 1.0)
    processed_today = max(0, int(document.get("processed_today", 0)))
    active_count = max(0, int(document.get("active_count", 0)))

    experience = _unit(
        attributes.get("experience_score"),
        min(0.9, 0.5 + processed_today / 200.0),
    )
    speed = _unit(attributes.get("speed_score"), capacity / max_capacity)
    reliability = _unit(attributes.get("reliability_score"), 0.75)
    success_rate = _unit(
        attributes.get("historical_success_rate"), reliability
    )
    average_time = _positive_float(
        attributes.get("historical_avg_processing_time"),
        max(5.0, 30.0 / capacity),
    )
    history_count = max(
        0,
        int(attributes.get("historical_orders_count", processed_today)),
    )
    settings_payload = dict(attributes)
    if "max_daily_limit" not in settings_payload and "daily_limit" in document:
        settings_payload["max_daily_limit"] = document["daily_limit"]

    return ExecutorProfile(
        user_id=executor_id,
        settings=ExecutorSettings.from_dict(settings_payload),
        experience_score=experience,
        speed_score=speed,
        reliability_score=reliability,
        historical_success_rate=success_rate,
        historical_avg_processing_time=average_time,
        historical_orders_count=history_count,
        capacity=capacity,
        active=str(document.get("active", "1")) in {"1", "true", "True"},
        daily_count=processed_today,
        skills=skills,
    )


def _json_object(value: object, name: str) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    parsed = json.loads(str(value))
    if not isinstance(parsed, dict):
        raise TypeError(f"{name} must be a JSON object")
    return parsed


def _json_strings(value: object, name: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    parsed = json.loads(str(value))
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        raise TypeError(f"{name} must be a JSON string array")
    return tuple(parsed)


def _unit(value: object, default: float) -> float:
    if value is None:
        return max(0.0, min(1.0, default))
    result = float(value)
    if not isfinite(result):
        raise ValueError("score must be finite")
    return max(0.0, min(1.0, result))


def _positive_float(value: object, default: float) -> float:
    if value is None:
        return default
    result = float(value)
    if not isfinite(result) or result <= 0:
        raise ValueError("value must be finite and positive")
    return result

