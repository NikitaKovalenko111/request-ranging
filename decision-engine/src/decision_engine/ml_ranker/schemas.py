from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite


def _unit_interval(name: str, value: float) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class Order:
    id: str
    timestamp: datetime
    complexity: float
    urgency: float
    estimated_effort_score: float = 0.5
    keyword_count_score: float = 0.0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("order id cannot be empty")
        _unit_interval("complexity", self.complexity)
        _unit_interval("urgency", self.urgency)
        _unit_interval("estimated_effort_score", self.estimated_effort_score)
        _unit_interval("keyword_count_score", self.keyword_count_score)


@dataclass(frozen=True, slots=True)
class Executor:
    id: str
    experience_score: float
    speed_score: float
    reliability_score: float
    historical_success_rate: float
    historical_avg_processing_time: float
    historical_orders_count: int
    skill_match_score: float = 0.0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("executor id cannot be empty")
        _unit_interval("experience_score", self.experience_score)
        _unit_interval("speed_score", self.speed_score)
        _unit_interval("reliability_score", self.reliability_score)
        _unit_interval("historical_success_rate", self.historical_success_rate)
        _unit_interval("skill_match_score", self.skill_match_score)
        if not isfinite(self.historical_avg_processing_time):
            raise ValueError("historical_avg_processing_time must be finite")
        if self.historical_avg_processing_time <= 0:
            raise ValueError("historical_avg_processing_time must be positive")
        if self.historical_orders_count < 0:
            raise ValueError("historical_orders_count cannot be negative")


@dataclass(frozen=True, slots=True)
class RankedExecutor:
    executor_id: str
    score: float
    rank: int

    def as_dict(self) -> dict[str, str | float | int]:
        return {
            "executor_id": self.executor_id,
            "score": self.score,
            "rank": self.rank,
        }

