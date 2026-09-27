from datetime import UTC, datetime

import pytest

from decision_engine.ml_ranker.feature_builder import FEATURE_COLUMNS, FeatureBuilder
from decision_engine.ml_ranker.schemas import Executor, Order


def test_feature_builder_matches_stable_contract() -> None:
    order = Order("O1", datetime.now(UTC), complexity=0.8, urgency=0.7)
    executor = Executor(
        "E1",
        experience_score=0.9,
        speed_score=0.6,
        reliability_score=0.95,
        historical_success_rate=0.92,
        historical_avg_processing_time=15.0,
        historical_orders_count=100,
    )

    features = FeatureBuilder().build(order, executor)

    assert tuple(features) == FEATURE_COLUMNS
    assert features["experience_fit"] == pytest.approx(0.9)
    assert features["urgency_speed_fit"] == pytest.approx(0.9)
    assert features["experience_gap"] == pytest.approx(0.1)
    assert features["speed_gap"] == pytest.approx(-0.1)
    assert features["processing_speed_score"] == pytest.approx(2 / 3)
    assert "current_load" not in features
    assert "eligible" not in features


@pytest.mark.parametrize("field", ["complexity", "urgency"])
def test_order_scores_must_be_normalized(field: str) -> None:
    values = {"complexity": 0.5, "urgency": 0.5, field: 1.1}

    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        Order("O1", datetime.now(UTC), **values)


def test_executor_history_must_be_valid() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        Executor("E1", 0.5, 0.5, 0.5, 0.5, 10.0, -1)

