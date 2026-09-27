from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import json

import numpy as np
import pandas as pd

from ..feature_extractor import (
    FeatureCandidate,
    FeatureExtractionRequest,
    FeatureExtractor,
    HeuristicFeatureExtractor,
)
from .feature_builder import FEATURE_COLUMNS, FeatureBuilder
from .schemas import Executor, Order


SKILL_CATALOG: tuple[str, ...] = (
    'python',
    'java',
    'go',
    'postgresql',
    'kafka',
    'redis',
    'docker',
    'kubernetes',
    'machine-learning',
    'rest-api',
    'frontend',
    'analytics',
)


@dataclass(frozen=True, slots=True)
class SyntheticGeneratorConfig:
    n_orders: int = 5_000
    candidates_per_order: int = 10
    executor_pool_size: int = 500
    seed: int = 42

    def __post_init__(self) -> None:
        if self.n_orders <= 0:
            raise ValueError('n_orders must be positive')
        if self.candidates_per_order < 2:
            raise ValueError('candidates_per_order must be at least 2')
        if self.executor_pool_size < self.candidates_per_order:
            raise ValueError('executor pool is smaller than a candidate group')


@dataclass(frozen=True, slots=True)
class SyntheticExecutor:
    profile: Executor
    skills: tuple[str, ...]


class SyntheticDataGenerator:
    '''Creates text, extracts features, and builds grouped ranking rows.'''

    def __init__(
        self,
        config: SyntheticGeneratorConfig,
        feature_builder: FeatureBuilder | None = None,
        feature_extractor: FeatureExtractor | None = None,
    ) -> None:
        self._config = config
        self._feature_builder = feature_builder or FeatureBuilder()
        self._feature_extractor = feature_extractor or HeuristicFeatureExtractor(
            max_keywords=24
        )
        self._rng = np.random.default_rng(config.seed)

    def generate(self) -> pd.DataFrame:
        executors = self._generate_executor_pool()
        rows: list[dict[str, object]] = []
        started_at = datetime(2026, 1, 1, tzinfo=UTC)

        for order_index in range(self._config.n_orders):
            candidate_indexes = self._rng.choice(
                len(executors),
                size=self._config.candidates_per_order,
                replace=False,
            )
            candidates = [executors[int(index)] for index in candidate_indexes]
            required_skills = tuple(
                str(skill)
                for skill in self._rng.choice(
                    SKILL_CATALOG,
                    size=int(self._rng.integers(2, 5)),
                    replace=False,
                )
            )
            text = self._build_order_text(required_skills)
            order_id = f'O{order_index:06d}'
            extracted = self._feature_extractor.extract(
                FeatureExtractionRequest(
                    order_id=order_id,
                    text=text,
                    candidates=tuple(
                        FeatureCandidate(item.profile.id, item.skills)
                        for item in candidates
                    ),
                )
            )
            order = Order(
                id=order_id,
                timestamp=started_at + timedelta(minutes=order_index),
                complexity=extracted.complexity,
                urgency=extracted.urgency,
                estimated_effort_score=extracted.estimated_effort_score,
                keyword_count_score=extracted.keyword_count_score,
            )

            order_rows: list[dict[str, object]] = []
            qualities: list[float] = []
            for item in candidates:
                executor = replace(
                    item.profile,
                    skill_match_score=extracted.skill_match_scores.get(
                        item.profile.id,
                        0.0,
                    ),
                )
                features = self._feature_builder.build(order, executor)
                quality = self._true_quality(order, executor, features)
                order_rows.append(
                    {
                        'order_id': order.id,
                        'order_timestamp': order.timestamp.isoformat(),
                        'order_text': text,
                        'extracted_language': extracted.language,
                        'extracted_estimated_effort': extracted.estimated_effort,
                        'extracted_keywords': json.dumps(
                            extracted.keywords,
                            ensure_ascii=False,
                        ),
                        'executor_id': executor.id,
                        **features,
                    }
                )
                qualities.append(quality)

            for row, relevance in zip(
                order_rows,
                self._relative_relevances(qualities),
                strict=True,
            ):
                row['relevance'] = relevance
            rows.extend(order_rows)

        columns = [
            'order_id',
            'order_timestamp',
            'order_text',
            'extracted_language',
            'extracted_estimated_effort',
            'extracted_keywords',
            'executor_id',
            *FEATURE_COLUMNS,
            'relevance',
        ]
        return pd.DataFrame(rows, columns=columns)

    def _generate_executor_pool(self) -> list[SyntheticExecutor]:
        executors = []
        for index in range(self._config.executor_pool_size):
            experience = float(self._rng.beta(2.2, 1.8))
            speed = float(self._rng.beta(2.0, 2.0))
            reliability = float(self._rng.beta(4.5, 1.5))
            history_count = int(self._rng.integers(0, 1_001))
            success = float(
                np.clip(
                    0.20
                    + 0.52 * reliability
                    + 0.20 * experience
                    + self._rng.normal(0.0, 0.06),
                    0.0,
                    1.0,
                )
            )
            average_time = float(
                max(1.0, 5.0 + 45.0 * (1.0 - speed) + self._rng.normal(0.0, 3.0))
            )
            skills = tuple(
                str(skill)
                for skill in self._rng.choice(
                    SKILL_CATALOG,
                    size=int(self._rng.integers(3, 7)),
                    replace=False,
                )
            )
            executors.append(
                SyntheticExecutor(
                    profile=Executor(
                        id=f'E{index:05d}',
                        experience_score=experience,
                        speed_score=speed,
                        reliability_score=reliability,
                        historical_success_rate=success,
                        historical_avg_processing_time=average_time,
                        historical_orders_count=history_count,
                    ),
                    skills=skills,
                )
            )
        return executors

    def _build_order_text(self, required_skills: tuple[str, ...]) -> str:
        complexity_level = int(self._rng.integers(0, 4))
        urgency_level = int(self._rng.integers(0, 4))
        complexity_text = (
            'routine configuration change',
            'service integration and diagnostics',
            'integration migration and diagnostics across services',
            'distributed architecture integration migration and diagnostics',
        )[complexity_level]
        urgency_text = (
            'planned work without a strict deadline',
            'normal business priority',
            'urgent work with a close deadline',
            'critical incident requiring urgent action immediately',
        )[urgency_level]
        details = ' '.join(['implementation validation'] * (1 + complexity_level * 3))
        return (
            f'{urgency_text}. {complexity_text}. '
            f'Required skills: {" ".join(required_skills)}. {details}.'
        )

    def _true_quality(
        self,
        order: Order,
        executor: Executor,
        features: dict[str, float],
    ) -> float:
        nonlinear_capability = min(
            executor.experience_score,
            executor.reliability_score,
        ) * order.complexity
        urgent_processing = (
            features['processing_speed_score'] * (0.4 + 0.6 * order.urgency)
        )
        quality = (
            0.18 * features['experience_fit']
            + 0.14 * features['urgency_speed_fit']
            + 0.12 * executor.reliability_score
            + 0.10 * features['success_confidence']
            + 0.08 * urgent_processing
            + 0.08 * nonlinear_capability
            + 0.08 * executor.historical_success_rate
            + 0.16 * executor.skill_match_score
            + 0.06 * features['skill_experience_synergy']
            + float(self._rng.normal(0.0, 0.035))
        )
        return float(np.clip(quality, 0.0, 1.0))

    @staticmethod
    def _relative_relevances(qualities: list[float]) -> list[int]:
        ordered_indexes = sorted(
            range(len(qualities)),
            key=lambda index: (-qualities[index], index),
        )
        relevance = [0] * len(qualities)
        count = len(qualities)
        for position, index in enumerate(ordered_indexes):
            percentile = position / count
            if percentile < 0.10:
                relevance[index] = 3
            elif percentile < 0.30:
                relevance[index] = 2
            elif percentile < 0.70:
                relevance[index] = 1
        return relevance
