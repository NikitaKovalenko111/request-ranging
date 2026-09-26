from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log2
from typing import Sequence

from catboost import CatBoostRanker
import numpy as np
import pandas as pd

from .feature_builder import FEATURE_COLUMNS
from .inference import HeuristicRanker


@dataclass(frozen=True, slots=True)
class RankingMetrics:
    ndcg_at_k: float
    mrr: float
    hit_rate_at_1: float
    evaluated_groups: int

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def heuristic_scores(frame: pd.DataFrame) -> np.ndarray:
    return frame.apply(HeuristicRanker.score_features, axis=1).to_numpy(dtype=float)


def evaluate_model(
    model: CatBoostRanker,
    test_frame: pd.DataFrame,
    *,
    k: int = 5,
) -> dict[str, RankingMetrics]:
    ml_scores = np.asarray(model.predict(test_frame.loc[:, FEATURE_COLUMNS]), dtype=float)
    return {
        "heuristic": ranking_metrics(test_frame, heuristic_scores(test_frame), k=k),
        "ml": ranking_metrics(test_frame, ml_scores, k=k),
    }


def ranking_metrics(
    frame: pd.DataFrame,
    scores: Sequence[float],
    *,
    k: int = 5,
) -> RankingMetrics:
    if k <= 0:
        raise ValueError("k must be positive")
    if len(frame) != len(scores):
        raise ValueError("one score is required for every dataset row")

    evaluated = 0
    ndcg_values = []
    reciprocal_ranks = []
    hits = []
    scored_frame = frame.loc[:, ["order_id", "relevance"]].copy()
    scored_frame["score"] = np.asarray(scores, dtype=float)

    for _, group in scored_frame.groupby("order_id", sort=False):
        relevance = group["relevance"].to_numpy(dtype=float)
        if relevance.max(initial=0.0) <= 0:
            continue
        predicted_order = np.argsort(-group["score"].to_numpy(dtype=float), kind="stable")
        ideal_order = np.argsort(-relevance, kind="stable")
        cutoff = min(k, len(group))
        ideal_dcg = _dcg(relevance[ideal_order[:cutoff]])
        ndcg_values.append(_dcg(relevance[predicted_order[:cutoff]]) / ideal_dcg)

        best_relevance = relevance.max()
        best_positions = np.flatnonzero(relevance[predicted_order] == best_relevance)
        reciprocal_ranks.append(1.0 / (int(best_positions[0]) + 1))
        hits.append(float(relevance[predicted_order[0]] == best_relevance))
        evaluated += 1

    if evaluated == 0:
        return RankingMetrics(0.0, 0.0, 0.0, 0)
    return RankingMetrics(
        ndcg_at_k=float(np.mean(ndcg_values)),
        mrr=float(np.mean(reciprocal_ranks)),
        hit_rate_at_1=float(np.mean(hits)),
        evaluated_groups=evaluated,
    )


def _dcg(relevance: np.ndarray) -> float:
    gains = np.power(2.0, relevance) - 1.0
    discounts = np.log2(np.arange(len(relevance), dtype=float) + 2.0)
    return float(np.sum(gains / discounts))

