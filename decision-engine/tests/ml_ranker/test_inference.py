from datetime import UTC, datetime

import pytest

from decision_engine.ml_ranker.inference import HeuristicRanker
from decision_engine.ml_ranker.schemas import Executor, Order


def executor(executor_id: str, quality: float) -> Executor:
    return Executor(
        executor_id,
        experience_score=quality,
        speed_score=quality,
        reliability_score=quality,
        historical_success_rate=quality,
        historical_avg_processing_time=5.0 + 30.0 * (1.0 - quality),
        historical_orders_count=int(quality * 500),
    )


def test_heuristic_ranker_orders_candidates_and_returns_unit_scores() -> None:
    order = Order("O1", datetime.now(UTC), complexity=0.9, urgency=0.9)

    ranking = HeuristicRanker().rank(
        order,
        [executor("weak", 0.3), executor("strong", 0.9)],
    )

    assert [item.executor_id for item in ranking] == ["strong", "weak"]
    assert [item.rank for item in ranking] == [1, 2]
    assert all(0 <= item.score <= 1 for item in ranking)


def test_duplicate_candidate_is_rejected() -> None:
    order = Order("O1", datetime.now(UTC), complexity=0.5, urgency=0.5)
    candidate = executor("same", 0.5)

    with pytest.raises(ValueError, match="unique"):
        HeuristicRanker().rank(order, [candidate, candidate])

