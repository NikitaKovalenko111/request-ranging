from __future__ import annotations

from dataclasses import dataclass
from math import log1p
from typing import Mapping

from .schemas import Executor, Order


# This tuple is the stable model input contract. Identifiers, labels, runtime
# load and hard-constraint fields must never be added implicitly.
FEATURE_COLUMNS: tuple[str, ...] = (
    "order_complexity",
    "order_urgency",
    "order_estimated_effort",
    "order_keyword_count",
    "experience_score",
    "speed_score",
    "reliability_score",
    "historical_success_rate",
    "skill_match_score",
    "processing_speed_score",
    "history_confidence",
    "experience_fit",
    "urgency_speed_fit",
    "experience_gap",
    "speed_gap",
    "reliability_under_complexity",
    "success_confidence",
    "effort_experience_fit",
    "skill_experience_synergy",
)


@dataclass(frozen=True, slots=True)
class FeatureBuilder:
    history_count_scale: int = 1_000
    processing_time_scale_minutes: float = 30.0

    def __post_init__(self) -> None:
        if self.history_count_scale <= 0:
            raise ValueError("history_count_scale must be positive")
        if self.processing_time_scale_minutes <= 0:
            raise ValueError("processing_time_scale_minutes must be positive")

    def build(self, order: Order, executor: Executor) -> dict[str, float]:
        history_confidence = min(
            1.0,
            log1p(executor.historical_orders_count)
            / log1p(self.history_count_scale),
        )
        processing_speed_score = 1.0 / (
            1.0
            + executor.historical_avg_processing_time
            / self.processing_time_scale_minutes
        )

        features = {
            "order_complexity": order.complexity,
            "order_urgency": order.urgency,
            "order_estimated_effort": order.estimated_effort_score,
            "order_keyword_count": order.keyword_count_score,
            "experience_score": executor.experience_score,
            "speed_score": executor.speed_score,
            "reliability_score": executor.reliability_score,
            "historical_success_rate": executor.historical_success_rate,
            "skill_match_score": executor.skill_match_score,
            "processing_speed_score": processing_speed_score,
            "history_confidence": history_confidence,
            "experience_fit": 1.0
            - abs(order.complexity - executor.experience_score),
            "urgency_speed_fit": 1.0 - abs(order.urgency - executor.speed_score),
            "experience_gap": executor.experience_score - order.complexity,
            "speed_gap": executor.speed_score - order.urgency,
            "reliability_under_complexity": executor.reliability_score
            * (0.5 + 0.5 * order.complexity),
            "success_confidence": executor.historical_success_rate
            * history_confidence,
            "effort_experience_fit": 1.0
            - abs(order.estimated_effort_score - executor.experience_score),
            "skill_experience_synergy": executor.skill_match_score
            * (0.5 + 0.5 * executor.experience_score),
        }
        self.validate(features)
        return features

    @staticmethod
    def validate(features: Mapping[str, float]) -> None:
        actual = tuple(features.keys())
        if actual != FEATURE_COLUMNS:
            raise ValueError(
                f"feature contract mismatch: expected {FEATURE_COLUMNS}, got {actual}"
            )

