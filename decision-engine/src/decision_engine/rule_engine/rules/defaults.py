from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain import Executor, Order, OrderStatus, RuleViolation
from .base import Rule


def _violation(code: str, message: str, **details: Any) -> RuleViolation:
    return RuleViolation(code=code, message=message, details=details)


@dataclass(frozen=True, slots=True)
class ProcessableStatusRule:
    code: str = "order_status"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        if order.status is OrderStatus.PROCESSED:
            return None
        return _violation(
            self.code,
            "order is not in the processed state",
            actual=order.status.value,
            expected=OrderStatus.PROCESSED.value,
        )


@dataclass(frozen=True, slots=True)
class ActiveRule:
    code: str = "executor_active"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        if executor.active:
            return None
        return _violation(self.code, "executor is inactive")


@dataclass(frozen=True, slots=True)
class DailyLimitRule:
    code: str = "daily_limit"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        limit = executor.settings.max_daily_limit
        if limit is None or executor.daily_count < limit:
            return None
        return _violation(
            self.code,
            "executor daily limit has been reached",
            daily_count=executor.daily_count,
            max_daily_limit=limit,
        )


@dataclass(frozen=True, slots=True)
class AcceptedAmountRule:
    code: str = "accepted_amount_range"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        minimum = executor.settings.min_accept_sum
        maximum = executor.settings.max_accept_sum
        if minimum is not None and order.sum < minimum:
            return _violation(
                self.code,
                "order sum is below the accepted minimum",
                order_sum=order.sum,
                min_accept_sum=minimum,
            )
        if maximum is not None and order.sum > maximum:
            return _violation(
                self.code,
                "order sum is above the accepted maximum",
                order_sum=order.sum,
                max_accept_sum=maximum,
            )
        return None


@dataclass(frozen=True, slots=True)
class RejectedAmountRule:
    code: str = "rejected_amount_range"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        minimum = executor.settings.min_reject_sum
        maximum = executor.settings.max_reject_sum
        if minimum is None and maximum is None:
            return None

        above_minimum = minimum is None or order.sum >= minimum
        below_maximum = maximum is None or order.sum <= maximum
        if not (above_minimum and below_maximum):
            return None
        return _violation(
            self.code,
            "order sum is in the executor rejection range",
            order_sum=order.sum,
            min_reject_sum=minimum,
            max_reject_sum=maximum,
        )


@dataclass(frozen=True, slots=True)
class ClientMspRule:
    code: str = "client_msp"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        expected_values = executor.settings.client_msps
        expected = executor.settings.client_msp
        if expected_values:
            if order.client_msp in expected_values:
                return None
        elif expected is None or order.client_msp == expected:
            return None
        return _violation(
            self.code,
            "client_msp does not match executor settings",
            actual=order.client_msp,
            expected=list(expected_values) if expected_values else expected,
        )


@dataclass(frozen=True, slots=True)
class ExecutorMspRule:
    code: str = "executor_msp"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        expected_values = executor.settings.executor_msps
        expected = executor.settings.executor_msp
        if expected_values:
            if order.executor_msp in expected_values:
                return None
        elif expected is None or order.executor_msp == expected:
            return None
        return _violation(
            self.code,
            "executor_msp does not match executor settings",
            actual=order.executor_msp,
            expected=list(expected_values) if expected_values else expected,
        )


@dataclass(frozen=True, slots=True)
class OrderTypeRule:
    code: str = "order_type"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        expected_values = executor.settings.order_types
        expected = executor.settings.order_type
        if expected_values:
            if order.order_type in expected_values:
                return None
        elif expected is None or order.order_type == expected:
            return None
        return _violation(
            self.code,
            "order type is not supported by executor",
            actual=order.order_type.value,
            expected=[item.value for item in expected_values] if expected_values else (
                expected.value if expected is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class SubjectRule:
    code: str = "subject"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        expected_values = executor.settings.subjects
        expected = executor.settings.subject
        if expected_values:
            if str(order.subject) in expected_values:
                return None
        elif expected is None or order.subject == expected:
            return None
        return _violation(
            self.code,
            "order subject is not supported by executor",
            actual=str(order.subject),
            expected=list(expected_values) if expected_values else str(expected),
        )


@dataclass(frozen=True, slots=True)
class VipRule:
    code: str = "vip"

    def evaluate(self, order: Order, executor: Executor) -> RuleViolation | None:
        # vip in user_settings is treated as a capability. A VIP-capable executor
        # may still handle a regular order; a non-VIP executor may not handle VIP.
        if not order.vip or executor.settings.vip:
            return None
        return _violation(self.code, "executor is not allowed to handle VIP orders")


SYSTEM_RULES: tuple[Rule, ...] = (
    ProcessableStatusRule(),
    ActiveRule(),
    DailyLimitRule(),
)

# Kept as the public default for backwards compatibility. Configurable business
# constraints are loaded as dynamic JSON rules and are intentionally not here.
DEFAULT_RULES = SYSTEM_RULES

BUSINESS_RULES: tuple[Rule, ...] = (
    AcceptedAmountRule(),
    RejectedAmountRule(),
    ClientMspRule(),
    ExecutorMspRule(),
    OrderTypeRule(),
    SubjectRule(),
    VipRule(),
)

INTEGRATION_RULES: tuple[Rule, ...] = SYSTEM_RULES + BUSINESS_RULES
