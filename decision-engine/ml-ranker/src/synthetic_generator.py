from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from .feature_builder import FEATURE_COLUMNS, FeatureBuilder
from .schemas import Executor, Order


@dataclass(frozen=True, slots=True)
class SyntheticGeneratorConfig:
    n_orders: int = 5_000
    candidates_per_order: int = 10
    executor_pool_size: int = 500
    seed: int = 42

    def __post_init__(self) -> None:
        if self.n_orders <= 0:
            raise ValueError("n_orders must be positive")
        if self.candidates_per_order < 2:
            raise ValueError("candidates_per_order must be at least 2")
        if self.executor_pool_size < self.candidates_per_order:
            raise ValueError("executor pool is smaller than a candidate group")


class SyntheticDataGenerator:
    """Creates a reproducible demo environment, not production ground truth."""

    def __init__(
        self,
        config: SyntheticGeneratorConfig,
        feature_builder: FeatureBuilder | None = None,
    ) -> None:
        self._config = config
        self._feature_builder = feature_builder or FeatureBuilder()
        self._rng = np.random.default_rng(config.seed)

    def generate(self) -> pd.DataFrame:
        executors = self._generate_executor_pool()
        rows: list[dict[str, object]] = []
        started_at = datetime(2026, 1, 1, tzinfo=UTC)

        for order_index in range(self._config.n_orders):
            order = Order(
                id=f"O{order_index:06d}",
                timestamp=started_at + timedelta(minutes=order_index),
                complexity=float(self._rng.beta(2.0, 2.0)),
                urgency=float(self._rng.beta(1.8, 2.2)),
            )
            candidate_indexes = self._rng.choice(
                len(executors),
                size=self._config.candidates_per_order,
                replace=False,
            )
            for candidate_index in candidate_indexes:
                executor = executors[int(candidate_index)]
                features = self._feature_builder.build(order, executor)
                quality = self._true_quality(order, executor, features)
                rows.append(
                    {
                        "order_id": order.id,
                        "order_timestamp": order.timestamp.isoformat(),
                        "executor_id": executor.id,
                        **features,
                        "relevance": self._to_relevance(quality),
                    }
                )

        columns = [
            "order_id",
            "order_timestamp",
            "executor_id",
            *FEATURE_COLUMNS,
            "relevance",
        ]
        return pd.DataFrame(rows, columns=columns)

    def _generate_executor_pool(self) -> list[Executor]:
        executors = []
        for index in range(self._config.executor_pool_size):
            experience = float(self._rng.beta(2.2, 1.8))
            speed = float(self._rng.beta(2.0, 2.0))
            reliability = float(self._rng.beta(4.5, 1.5))
            history_count = int(self._rng.integers(0, 1_001))
            success = float(
                np.clip(
                    0.20 + 0.52 * reliability + 0.20 * experience
                    + self._rng.normal(0.0, 0.06),
                    0.0,
                    1.0,
                )
            )
            average_time = float(
                max(1.0, 5.0 + 45.0 * (1.0 - speed) + self._rng.normal(0.0, 3.0))
            )
            executors.append(
                Executor(
                    id=f"E{index:05d}",
                    experience_score=experience,
                    speed_score=speed,
                    reliability_score=reliability,
                    historical_success_rate=success,
                    historical_avg_processing_time=average_time,
                    historical_orders_count=history_count,
                )
            )
        return executors

    def _true_quality(
        self,
        order: Order,
        executor: Executor,
        features: dict[str, float],
    ) -> float:
        # This formula is used only to simulate outcomes. It is deliberately not
        # imported by FeatureBuilder, training or inference code.
        nonlinear_capability = min(
            executor.experience_score,
            executor.reliability_score,
        ) * order.complexity
        urgent_processing = (
            features["processing_speed_score"] * (0.4 + 0.6 * order.urgency)
        )
        quality = (
            0.25 * features["experience_fit"]
            + 0.19 * features["urgency_speed_fit"]
            + 0.15 * executor.reliability_score
            + 0.13 * features["success_confidence"]
            + 0.10 * urgent_processing
            + 0.10 * nonlinear_capability
            + 0.08 * executor.historical_success_rate
            + float(self._rng.normal(0.0, 0.035))
        )
        return float(np.clip(quality, 0.0, 1.0))

    @staticmethod
    def _to_relevance(quality: float) -> int:
        if quality >= 0.85:
            return 3
        if quality >= 0.65:
            return 2
        if quality >= 0.40:
            return 1
        return 0

