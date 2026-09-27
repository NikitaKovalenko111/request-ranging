from datetime import UTC, datetime, timedelta
from math import isinf

import pytest

from decision_engine.balancer import (
    BalancerCandidate,
    ExecutorLoad,
    balance_candidates,
    effective_load,
)


def test_executor_without_load_has_lower_effective_load() -> None:
    assert effective_load(ExecutorLoad(), capacity=1.0) == 0.0
    assert effective_load(ExecutorLoad(active_weight=2.0), capacity=1.0) == 2.0


def test_pending_weight_affects_load_like_active_weight() -> None:
    active = effective_load(ExecutorLoad(active_weight=4.0), capacity=2.0)
    pending = effective_load(ExecutorLoad(pending_weight=4.0), capacity=2.0)

    assert active == pending == 2.0


def test_capacity_normalizes_weight() -> None:
    load = ExecutorLoad(active_weight=10.0, pending_weight=2.0)

    assert effective_load(load, capacity=2.0) == 6.0
    assert effective_load(load, capacity=4.0) == 3.0


def test_non_positive_capacity_ranks_last_without_exception() -> None:
    assert isinf(effective_load(ExecutorLoad(), capacity=0.0))
    result = balance_candidates(
        [
            BalancerCandidate("invalid", 0.99, capacity=0.0),
            BalancerCandidate("valid", 0.50, capacity=1.0),
        ],
        {},
    )

    assert [item.executor_id for item in result] == ["valid", "invalid"]


def test_example_from_specification_orders_a_before_b() -> None:
    result = balance_candidates(
        [
            BalancerCandidate("A", 0.8, capacity=2.0),
            BalancerCandidate("B", 0.8, capacity=1.0),
        ],
        {
            "A": ExecutorLoad(active_weight=10.0),
            "B": ExecutorLoad(active_weight=4.0, pending_weight=2.0),
        },
    )

    assert [(item.executor_id, item.effective_load) for item in result] == [
        ("A", 5.0),
        ("B", 6.0),
    ]


def test_equal_load_uses_open_count_then_ml_score_as_tie_breakers() -> None:
    result = balance_candidates(
        [
            BalancerCandidate("more-open", 0.99),
            BalancerCandidate("high-score", 0.90),
            BalancerCandidate("low-score", 0.80),
        ],
        {
            "more-open": ExecutorLoad(active_count=2, active_weight=2.0),
            "high-score": ExecutorLoad(active_count=1, active_weight=2.0),
            "low-score": ExecutorLoad(active_count=1, active_weight=2.0),
        },
    )

    assert [item.executor_id for item in result] == [
        "high-score",
        "low-score",
        "more-open",
    ]


def test_oldest_assignment_and_id_make_order_deterministic() -> None:
    now = datetime.now(UTC)
    result = balance_candidates(
        [
            BalancerCandidate("recent", 0.8),
            BalancerCandidate("old", 0.8),
            BalancerCandidate("never-b", 0.8),
            BalancerCandidate("never-a", 0.8),
        ],
        {
            "recent": ExecutorLoad(last_assignment_at=now),
            "old": ExecutorLoad(last_assignment_at=now - timedelta(hours=1)),
        },
    )

    assert [item.executor_id for item in result] == [
        "never-a",
        "never-b",
        "old",
        "recent",
    ]
    assert [item.rank for item in result] == [1, 2, 3, 4]

