from __future__ import annotations

from collections.abc import Sequence

from .load_repository import LoadRepository
from .schemas import BalancerCandidate, BalancerOrder, BalancerValidationError, BalancedCandidate
from .scoring import balance_candidates


class Balancer:
    """Orchestrates one batch load read and pure in-memory balancing."""

    def __init__(self, load_repository: LoadRepository) -> None:
        self._load_repository = load_repository

    async def balance(
        self,
        order: BalancerOrder,
        candidates: Sequence[BalancerCandidate],
    ) -> list[BalancedCandidate]:
        del order
        if not candidates:
            return []
        self._validate_candidates(candidates)
        candidate_list = list(candidates)
        executor_ids = [candidate.executor_id for candidate in candidate_list]
        loads = await self._load_repository.get_many(executor_ids)
        return balance_candidates(candidate_list, loads)

    @staticmethod
    def _validate_candidates(candidates: Sequence[BalancerCandidate]) -> None:
        executor_ids = [candidate.executor_id for candidate in candidates]
        if len(executor_ids) != len(set(executor_ids)):
            raise BalancerValidationError("candidates contain duplicate executor ids")
