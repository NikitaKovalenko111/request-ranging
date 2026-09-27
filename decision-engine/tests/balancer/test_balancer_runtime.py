import asyncio

import pytest

from decision_engine.balancer import (
    Balancer,
    BalancerCandidate,
    BalancerOrder,
    ExecutorLoad,
    LoadRepositoryError,
)


class RecordingRepository:
    def __init__(self, loads=None) -> None:
        self.loads = loads or {}
        self.calls = []

    async def get_many(self, executor_ids):
        self.calls.append(list(executor_ids))
        return dict(self.loads)


class FailingRepository:
    async def get_many(self, executor_ids):
        raise LoadRepositoryError("Redis runtime load is unavailable")


def test_balancer_reads_all_candidates_in_one_batch() -> None:
    async def scenario() -> None:
        repository = RecordingRepository(
            {
                "A": ExecutorLoad(active_weight=5.0),
                "B": ExecutorLoad(active_weight=1.0),
                "C": ExecutorLoad(active_weight=3.0),
            }
        )
        result = await Balancer(repository).balance(
            BalancerOrder("O1"),
            [
                BalancerCandidate("A", 0.9),
                BalancerCandidate("B", 0.8),
                BalancerCandidate("C", 0.7),
            ],
        )

        assert repository.calls == [["A", "B", "C"]]
        assert [item.executor_id for item in result] == ["B", "C", "A"]

    asyncio.run(scenario())


def test_repository_omission_is_treated_as_zero_load() -> None:
    async def scenario() -> None:
        result = await Balancer(
            RecordingRepository({"busy": ExecutorLoad(active_weight=5.0)})
        ).balance(
            BalancerOrder("O1"),
            [
                BalancerCandidate("busy", 0.9),
                BalancerCandidate("missing", 0.8),
            ],
        )

        assert result[0].executor_id == "missing"
        assert result[0].effective_load == 0.0

    asyncio.run(scenario())


def test_empty_candidates_return_without_repository_call() -> None:
    async def scenario() -> None:
        repository = RecordingRepository()

        result = await Balancer(repository).balance(BalancerOrder("O1"), [])

        assert result == []
        assert repository.calls == []

    asyncio.run(scenario())


def test_repository_error_is_not_silently_converted_to_zero_load() -> None:
    async def scenario() -> None:
        with pytest.raises(LoadRepositoryError, match="unavailable"):
            await Balancer(FailingRepository()).balance(
                BalancerOrder("O1"),
                [BalancerCandidate("A", 0.9)],
            )

    asyncio.run(scenario())

