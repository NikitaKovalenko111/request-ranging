import pandas as pd
import pytest

from decision_engine.ml_ranker.evaluate import ranking_metrics


def test_perfect_ranking_scores_one() -> None:
    frame = pd.DataFrame(
        {
            "order_id": ["O1", "O1", "O1", "O2", "O2", "O2"],
            "relevance": [3, 2, 0, 0, 1, 3],
        }
    )

    metrics = ranking_metrics(frame, [3, 2, 0, 0, 1, 3], k=3)

    assert metrics.ndcg_at_k == pytest.approx(1.0)
    assert metrics.mrr == pytest.approx(1.0)
    assert metrics.hit_rate_at_1 == pytest.approx(1.0)
    assert metrics.evaluated_groups == 2


def test_bad_ranking_is_worse_than_perfect_ranking() -> None:
    frame = pd.DataFrame(
        {"order_id": ["O1", "O1", "O1"], "relevance": [3, 1, 0]}
    )

    perfect = ranking_metrics(frame, [3, 1, 0], k=3)
    reversed_ranking = ranking_metrics(frame, [0, 1, 3], k=3)

    assert reversed_ranking.ndcg_at_k < perfect.ndcg_at_k
    assert reversed_ranking.mrr < perfect.mrr
    assert reversed_ranking.hit_rate_at_1 == 0.0

