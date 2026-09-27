from __future__ import annotations

from math import inf, isfinite

from .schemas import BalancerCandidate, BalancedCandidate, ExecutorLoad


def effective_load(load: ExecutorLoad, capacity: float) -> float:
    """Return normalized active + pending weight; invalid capacity ranks last."""
    if not isfinite(capacity) or capacity <= 0:
        return inf
    return (load.active_weight + load.pending_weight) / capacity


def balance_candidates(
    candidates: list[BalancerCandidate],
    loads: dict[str, ExecutorLoad],
) -> list[BalancedCandidate]:
    evaluated = [
        (
            candidate,
            loads.get(candidate.executor_id, ExecutorLoad()),
            effective_load(
                loads.get(candidate.executor_id, ExecutorLoad()),
                candidate.capacity,
            ),
        )
        for candidate in candidates
    ]
    evaluated.sort(key=_sort_key)
    return [
        BalancedCandidate(
            executor_id=candidate.executor_id,
            rank=rank,
            ml_score=candidate.ml_score,
            effective_load=load_value,
            capacity=candidate.capacity,
            active_count=load.active_count,
            pending_count=load.pending_count,
            processed_today=load.processed_today,
            last_assignment_at=load.last_assignment_at,
        )
        for rank, (candidate, load, load_value) in enumerate(evaluated, start=1)
    ]


def _sort_key(
    item: tuple[BalancerCandidate, ExecutorLoad, float],
) -> tuple[float, int, float, int, float, str]:
    candidate, load, load_value = item
    open_count = load.active_count + load.pending_count
    last_assignment = (
        float("-inf")
        if load.last_assignment_at is None
        else load.last_assignment_at.timestamp()
    )
    return (
        load_value,
        open_count,
        -candidate.ml_score,
        load.processed_today,
        last_assignment,
        candidate.executor_id,
    )

