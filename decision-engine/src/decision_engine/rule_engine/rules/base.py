from typing import Protocol

from ..domain import Executor, Order, RuleViolation


class Rule(Protocol):
    """A single independently testable hard constraint."""

    code: str

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        """Return None when the pair is allowed, otherwise explain the rejection."""
        ...

