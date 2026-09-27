from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import isfinite
from typing import Any, Mapping


class BalancerValidationError(ValueError):
    """Input does not satisfy the Balancer runtime contract."""


@dataclass(frozen=True, slots=True)
class BalancerOrder:
    order_id: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.order_id:
            raise BalancerValidationError("order_id cannot be empty")
        if not isfinite(self.weight) or self.weight <= 0:
            raise BalancerValidationError("order weight must be finite and positive")


@dataclass(frozen=True, slots=True)
class BalancerCandidate:
    executor_id: str
    ml_score: float
    capacity: float = 1.0

    def __post_init__(self) -> None:
        if not self.executor_id:
            raise BalancerValidationError("executor_id cannot be empty")
        if not isfinite(self.ml_score) or not 0.0 <= self.ml_score <= 1.0:
            raise BalancerValidationError("ml_score must be finite and in [0, 1]")
        if not isfinite(self.capacity):
            raise BalancerValidationError("capacity must be finite")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> BalancerCandidate:
        score = value.get("ml_score", value.get("score"))
        if score is None:
            raise BalancerValidationError("candidate has no ml_score")
        return cls(
            executor_id=str(value["executor_id"]),
            ml_score=float(score),
            capacity=float(value.get("capacity", 1.0)),
        )


@dataclass(frozen=True, slots=True)
class ExecutorLoad:
    active_count: int = 0
    active_weight: float = 0.0
    pending_count: int = 0
    pending_weight: float = 0.0
    processed_today: int = 0
    last_assignment_at: datetime | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("active_count", self.active_count),
            ("pending_count", self.pending_count),
            ("processed_today", self.processed_today),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BalancerValidationError(f"{name} must be a non-negative integer")
        for name, value in (
            ("active_weight", self.active_weight),
            ("pending_weight", self.pending_weight),
        ):
            if not isfinite(value) or value < 0:
                raise BalancerValidationError(f"{name} must be finite and non-negative")
        if self.last_assignment_at is not None:
            if self.last_assignment_at.tzinfo is None:
                raise BalancerValidationError("last_assignment_at must be timezone-aware")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ExecutorLoad:
        timestamp = value.get("last_assignment_at")
        return cls(
            active_count=int(value.get("active_count", 0)),
            active_weight=float(value.get("active_weight", 0.0)),
            pending_count=int(value.get("pending_count", 0)),
            pending_weight=float(value.get("pending_weight", 0.0)),
            processed_today=int(value.get("processed_today", 0)),
            last_assignment_at=_parse_datetime(timestamp),
        )


@dataclass(frozen=True, slots=True)
class BalancedCandidate:
    executor_id: str
    rank: int
    ml_score: float
    effective_load: float
    capacity: float
    active_count: int
    pending_count: int
    processed_today: int
    last_assignment_at: datetime | None

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.last_assignment_at is not None:
            result["last_assignment_at"] = self.last_assignment_at.isoformat()
        return result


def _parse_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise BalancerValidationError("last_assignment_at is not ISO-8601") from error
    else:
        raise BalancerValidationError("last_assignment_at must be a string or datetime")
    if result.tzinfo is None:
        raise BalancerValidationError("last_assignment_at must be timezone-aware")
    return result.astimezone(UTC)

