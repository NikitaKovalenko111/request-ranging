from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from math import exp
from pathlib import Path
from typing import Protocol, Sequence

from catboost import CatBoostRanker
import pandas as pd

from config import DEFAULT_CONFIG
from .feature_builder import FEATURE_COLUMNS, FeatureBuilder
from .schemas import Executor, Order, RankedExecutor


class Ranker(Protocol):
    model_version: str

    def rank(
        self, order: Order, candidates: Sequence[Executor]
    ) -> list[RankedExecutor]: ...


class HeuristicRanker:
    """Transparent cold-start baseline and local fallback."""

    model_version = "heuristic-v1"

    def __init__(self, feature_builder: FeatureBuilder | None = None) -> None:
        self._feature_builder = feature_builder or FeatureBuilder()

    def rank(
        self, order: Order, candidates: Sequence[Executor]
    ) -> list[RankedExecutor]:
        _ensure_unique_candidates(candidates)
        scored = []
        for executor in candidates:
            features = self._feature_builder.build(order, executor)
            score = self.score_features(features)
            scored.append((executor.id, score))
        return _rank(scored)

    @staticmethod
    def score_features(features: dict[str, float] | pd.Series) -> float:
        return float(
            0.28 * features["experience_fit"]
            + 0.22 * features["urgency_speed_fit"]
            + 0.20 * features["reliability_score"]
            + 0.18 * features["historical_success_rate"]
            + 0.07 * features["processing_speed_score"]
            + 0.05 * features["history_confidence"]
        )


class MLRanker:
    def __init__(
        self,
        model_path: Path,
        metadata_path: Path,
        feature_builder: FeatureBuilder | None = None,
    ) -> None:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        model_features = tuple(metadata["feature_columns"])
        if model_features != FEATURE_COLUMNS:
            raise ValueError(
                "saved model feature contract differs from the runtime contract"
            )

        self.model_version = str(metadata["model_version"])
        self._feature_builder = feature_builder or FeatureBuilder()
        self._model = CatBoostRanker()
        self._model.load_model(str(model_path))

    def rank(
        self, order: Order, candidates: Sequence[Executor]
    ) -> list[RankedExecutor]:
        _ensure_unique_candidates(candidates)
        if not candidates:
            return []

        rows = [self._feature_builder.build(order, executor) for executor in candidates]
        frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
        raw_scores = self._model.predict(frame)
        scored = [
            (executor.id, _sigmoid(float(raw_score)))
            for executor, raw_score in zip(candidates, raw_scores, strict=True)
        ]
        return _rank(scored)


def load_ranker_or_fallback(
    model_path: Path = DEFAULT_CONFIG.paths.model_path,
    metadata_path: Path = DEFAULT_CONFIG.paths.metadata_path,
) -> Ranker:
    try:
        return MLRanker(model_path, metadata_path)
    except (FileNotFoundError, OSError, ValueError, KeyError, json.JSONDecodeError):
        return HeuristicRanker()


def _ensure_unique_candidates(candidates: Sequence[Executor]) -> None:
    ids = [candidate.id for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate ids must be unique within an order")


def _rank(scored: list[tuple[str, float]]) -> list[RankedExecutor]:
    ordered = sorted(scored, key=lambda item: (-item[1], item[0]))
    return [
        RankedExecutor(executor_id=executor_id, score=score, rank=index)
        for index, (executor_id, score) in enumerate(ordered, start=1)
    ]


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + exp(-value))
    exponent = exp(value)
    return exponent / (1.0 + exponent)


def _demo_candidates() -> tuple[Order, list[Executor]]:
    order = Order(
        id="O-DEMO",
        timestamp=datetime.now(UTC),
        complexity=0.78,
        urgency=0.72,
    )
    candidates = [
        Executor("E-A", 0.90, 0.76, 0.94, 0.93, 11.0, 420),
        Executor("E-B", 0.65, 0.88, 0.84, 0.86, 8.0, 150),
        Executor("E-C", 0.79, 0.61, 0.91, 0.90, 17.0, 310),
    ]
    return order, candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local ranking example")
    parser.add_argument("--model", type=Path, default=DEFAULT_CONFIG.paths.model_path)
    parser.add_argument(
        "--metadata", type=Path, default=DEFAULT_CONFIG.paths.metadata_path
    )
    arguments = parser.parse_args()

    ranker = load_ranker_or_fallback(arguments.model, arguments.metadata)
    order, candidates = _demo_candidates()
    output = {
        "order_id": order.id,
        "model_version": ranker.model_version,
        "ranking": [item.as_dict() for item in ranker.rank(order, candidates)],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

