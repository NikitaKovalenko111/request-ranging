from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import UUID


class DomainValidationError(ValueError):
    """Raised when an incoming order or executor has an invalid shape."""


class OrderStatus(StrEnum):
    PROCESSED = "processed"
    AWAIT = "await"
    ACCEPT = "accept"
    REJECT = "reject"


class OrderType(StrEnum):
    ORDER_1 = "ORDER_1"
    ORDER_2 = "ORDER_2"
    ORDER_3 = "ORDER_3"
    LEGAL_REVIEW = "LEGAL_REVIEW"
    CONSULTATION = "CONSULTATION"
    CLAIM_PROCESSING = "CLAIM_PROCESSING"

    @classmethod
    def parse(cls, value: object) -> OrderType:
        # user_settings uses ORDER_TYPE_N, while order uses ORDER_N.
        normalized = str(value).upper().replace("ORDER_TYPE_", "ORDER_")
        try:
            return cls(normalized)
        except ValueError as error:
            raise DomainValidationError(f"unsupported order_type: {value!r}") from error


def _required(data: Mapping[str, Any], field_name: str) -> Any:
    value = data.get(field_name)
    if value is None:
        raise DomainValidationError(f"required field is missing: {field_name}")
    return value


def _optional_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise DomainValidationError(f"{field_name} must be an integer") from error


def _required_int(data: Mapping[str, Any], field_name: str) -> int:
    parsed = _optional_int(_required(data, field_name), field_name)
    assert parsed is not None
    return parsed


def _required_str(data: Mapping[str, Any], field_name: str) -> str:
    value = str(_required(data, field_name)).strip()
    if not value:
        raise DomainValidationError(f"{field_name} must be a non-empty string")
    return value


def _as_bool(value: object, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise DomainValidationError(f"{field_name} must be a boolean")


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    values = value if isinstance(value, (list, tuple, set)) else (value,)
    result = tuple(str(item).strip() for item in values if str(item).strip())
    return tuple(dict.fromkeys(result))


def _optional_scalar_string(value: object) -> str | None:
    if value is None or isinstance(value, (list, tuple, set)):
        return None
    result = str(value).strip()
    return result or None


@dataclass(frozen=True, slots=True)
class Order:
    id: str
    sum: int
    order_type: OrderType
    subject: UUID | str
    status: OrderStatus
    parent_id: int | str | None = None
    user_id: int | str | None = None
    client_msp: str | None = None
    executor_msp: str | None = None
    vip: bool = False
    text: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise DomainValidationError("id must be a non-empty string")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Order:
        try:
            status = OrderStatus(str(_required(data, "status")).lower())
            subject_value = _required(data, "subject")
            try:
                subject: UUID | str = UUID(str(subject_value))
            except ValueError:
                subject = _required_str(data, "subject")
        except ValueError as error:
            raise DomainValidationError(str(error)) from error

        return cls(
            id=_required_str(data, "id"),
            parent_id=data.get("parent_id"),
            user_id=data.get("user_id"),
            sum=_required_int(data, "sum"),
            client_msp=data.get("client_msp"),
            executor_msp=data.get("executor_msp"),
            order_type=OrderType.parse(_required(data, "order_type")),
            subject=subject,
            vip=_as_bool(data.get("vip", False), "vip"),
            text=data.get("text"),
            status=status,
        )


@dataclass(frozen=True, slots=True)
class ExecutorSettings:
    order_type: OrderType | None = None
    min_accept_sum: int | None = None
    max_accept_sum: int | None = None
    min_reject_sum: int | None = None
    max_reject_sum: int | None = None
    client_msp: str | None = None
    executor_msp: str | None = None
    subject: UUID | str | None = None
    vip: bool = False
    max_daily_limit: int | None = None
    order_types: tuple[OrderType, ...] = ()
    client_msps: tuple[str, ...] = ()
    executor_msps: tuple[str, ...] = ()
    subjects: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ExecutorSettings:
        subject_value = data.get("subject")
        if subject_value is None:
            subject: UUID | str | None = None
        else:
            try:
                subject = UUID(str(subject_value))
            except ValueError:
                subject = str(subject_value).strip() or None

        order_type_value = data.get("order_type")
        order_types = tuple(
            OrderType.parse(item) for item in _string_tuple(data.get("order_types"))
        )
        order_type = (
            OrderType.parse(order_type_value)
            if order_type_value is not None
            else (order_types[0] if order_types else None)
        )

        max_daily_limit = _optional_int(data.get("max_daily_limit"), "max_daily_limit")
        if max_daily_limit is not None and max_daily_limit < 0:
            raise DomainValidationError("max_daily_limit cannot be negative")

        return cls(
            min_accept_sum=_optional_int(data.get("min_accept_sum"), "min_accept_sum"),
            max_accept_sum=_optional_int(data.get("max_accept_sum"), "max_accept_sum"),
            min_reject_sum=_optional_int(data.get("min_reject_sum"), "min_reject_sum"),
            max_reject_sum=_optional_int(data.get("max_reject_sum"), "max_reject_sum"),
            client_msp=_optional_scalar_string(data.get("client_msp")),
            executor_msp=_optional_scalar_string(data.get("executor_msp")),
            order_type=order_type,
            subject=subject,
            vip=_as_bool(data.get("vip", data.get("vip_allowed", False)), "settings.vip"),
            max_daily_limit=max_daily_limit,
            order_types=order_types,
            client_msps=_string_tuple(data.get("client_msp")),
            executor_msps=_string_tuple(data.get("executor_msp")),
            subjects=_string_tuple(data.get("subjects")),
        )


@dataclass(frozen=True, slots=True)
class Executor:
    user_id: int | str
    settings: ExecutorSettings
    active: bool = True
    daily_count: int = 0

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], *, fallback_user_id: int | str | None = None
    ) -> Executor:
        user_id = data.get("user_id", data.get("id", fallback_user_id))
        if user_id is None:
            raise DomainValidationError("executor user_id is missing")

        settings_data = data.get("settings", data)
        if not isinstance(settings_data, Mapping):
            raise DomainValidationError("executor settings must be an object")

        daily_count = _optional_int(data.get("daily_count", 0), "daily_count")
        assert daily_count is not None
        if daily_count < 0:
            raise DomainValidationError("daily_count cannot be negative")

        parsed_user_id: int | str
        if isinstance(user_id, int) and not isinstance(user_id, bool):
            parsed_user_id = user_id
        else:
            parsed_user_id = str(user_id).strip()
            if not parsed_user_id:
                raise DomainValidationError("executor user_id cannot be empty")

        return cls(
            user_id=parsed_user_id,
            active=_as_bool(data.get("active", True), "active"),
            daily_count=daily_count,
            settings=ExecutorSettings.from_dict(settings_data),
        )


@dataclass(frozen=True, slots=True)
class RuleViolation:
    code: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    executor_id: int | str
    eligible: bool
    violations: tuple[RuleViolation, ...] = ()
    traces: tuple[Any, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "executor_id": self.executor_id,
            "eligible": self.eligible,
            "violations": [violation.as_dict() for violation in self.violations],
        }


    def trace_dict(self) -> dict[str, Any]:
        return {
            'executor_id': self.executor_id,
            'eligible': self.eligible,
            'violations': [violation.as_dict() for violation in self.violations],
            'rule_traces': [trace.as_dict() for trace in self.traces],
            'failed_conditions': [
                condition.as_dict()
                for trace in self.traces
                if not trace.result
                for condition in trace.conditions
                if not condition.result
            ],
        }


@dataclass(frozen=True, slots=True)
class FilterResult:
    order_id: str
    decisions: tuple[CandidateDecision, ...]

    @property
    def eligible_executor_ids(self) -> list[int | str]:
        return [decision.executor_id for decision in self.decisions if decision.eligible]

    @property
    def rejected(self) -> list[CandidateDecision]:
        return [decision for decision in self.decisions if not decision.eligible]

    def as_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "candidate_count": len(self.decisions),
            "eligible_executor_ids": self.eligible_executor_ids,
            "rejected": [decision.as_dict() for decision in self.rejected],
        }
