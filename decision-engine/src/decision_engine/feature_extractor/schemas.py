from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping


def _optional_unit_interval(name: str, value: float | None) -> None:
    if value is not None and (not isfinite(value) or not 0.0 <= value <= 1.0):
        raise ValueError(f'{name} must be in [0, 1]')


@dataclass(frozen=True, slots=True)
class FeatureCandidate:
    executor_id: str
    skills: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.executor_id:
            raise ValueError('executor_id cannot be empty')


@dataclass(frozen=True, slots=True)
class FeatureExtractionRequest:
    order_id: str
    text: str
    candidates: tuple[FeatureCandidate, ...]
    fallback_complexity: float | None = None
    fallback_urgency: float | None = None

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError('order_id cannot be empty')
        _optional_unit_interval('fallback_complexity', self.fallback_complexity)
        _optional_unit_interval('fallback_urgency', self.fallback_urgency)


@dataclass(frozen=True, slots=True)
class ExtractedFeatures:
    complexity: float
    urgency: float
    language: str | None = None
    estimated_effort: str | None = None
    keywords: tuple[str, ...] = ()
    skill_match_scores: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _optional_unit_interval('complexity', self.complexity)
        _optional_unit_interval('urgency', self.urgency)
        for executor_id, score in self.skill_match_scores.items():
            if not executor_id:
                raise ValueError('skill match executor_id cannot be empty')
            if not isfinite(score) or not 0.0 <= score <= 1.0:
                raise ValueError('skill match scores must be in [0, 1]')

    def as_dict(self) -> dict[str, Any]:
        return {
            'complexity': self.complexity,
            'urgency': self.urgency,
            'language': self.language,
            'estimated_effort': self.estimated_effort,
            'keywords': list(self.keywords),
            'skill_match_scores': dict(self.skill_match_scores),
        }

    @property
    def estimated_effort_score(self) -> float:
        return {
            'up_to_1h': 0.0,
            '1_to_4h': 1.0 / 3.0,
            '4_to_8h': 2.0 / 3.0,
            'over_8h': 1.0,
        }.get(self.estimated_effort, 0.5)

    @property
    def keyword_count_score(self) -> float:
        return min(len(self.keywords) / 24.0, 1.0)
