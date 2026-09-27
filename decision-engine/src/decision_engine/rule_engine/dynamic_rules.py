from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Any, Mapping, TypeAlias

from .domain import DomainValidationError


class RuleConfigurationError(ValueError):
    """Raised when a cached dynamic rule has an invalid definition."""


class OperandSource(StrEnum):
    ORDER = "order"
    EXECUTOR = "executor"
    CONSTANT = "constant"


class Operator(StrEnum):
    EQ = "EQ"
    NEQ = "NEQ"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    BETWEEN = "BETWEEN"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"


class GroupLogic(StrEnum):
    AND = "AND"
    OR = "OR"


@dataclass(frozen=True, slots=True)
class Operand:
    source: OperandSource
    field: str | None = None
    value: Any = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Operand:
        try:
            source = OperandSource(str(data["source"]).lower())
        except (KeyError, ValueError, TypeError) as error:
            raise RuleConfigurationError("operand.source is invalid") from error

        if source is OperandSource.CONSTANT:
            if "value" not in data:
                raise RuleConfigurationError("constant operand requires value")
            return cls(source=source, value=data["value"])

        field = data.get("field")
        if not isinstance(field, str) or not field:
            raise RuleConfigurationError(f"{source.value} operand requires field")
        return cls(source=source, field=field)


@dataclass(frozen=True, slots=True)
class Comparison:
    code: str
    left: Operand
    operator: Operator
    right: Operand | None = None


@dataclass(frozen=True, slots=True)
class ConditionGroup:
    logic: GroupLogic
    conditions: tuple[Condition, ...]


Condition: TypeAlias = Comparison | ConditionGroup


@dataclass(frozen=True, slots=True)
class DistributionRule:
    id: str
    name: str
    condition: Condition
    description: str | None = None
    enabled: bool = True
    priority: int = 100
    version: int = 1

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DistributionRule:
        rule_id = data.get("id")
        name = data.get("name")
        if not isinstance(rule_id, str) or not rule_id:
            raise RuleConfigurationError("rule.id must be a non-empty string")
        if not isinstance(name, str) or not name:
            raise RuleConfigurationError(f"rule {rule_id}: name must be a non-empty string")

        enabled = data.get("enabled", True)
        if not isinstance(enabled, bool):
            raise RuleConfigurationError(f"rule {rule_id}: enabled must be boolean")

        try:
            priority = int(data.get("priority", 100))
            version = int(data.get("version", 1))
        except (TypeError, ValueError) as error:
            raise RuleConfigurationError(
                f"rule {rule_id}: priority and version must be integers"
            ) from error
        if version < 1:
            raise RuleConfigurationError(f"rule {rule_id}: version must be positive")

        condition_data = data.get("condition")
        if not isinstance(condition_data, Mapping):
            raise RuleConfigurationError(f"rule {rule_id}: condition must be an object")

        return cls(
            id=rule_id,
            name=name,
            description=data.get("description"),
            enabled=enabled,
            priority=priority,
            version=version,
            condition=parse_condition(condition_data, path=f"rule {rule_id}.condition"),
        )


def parse_condition(data: Mapping[str, Any], *, path: str = "condition") -> Condition:
    if "logic" in data:
        try:
            logic = GroupLogic(str(data["logic"]).upper())
        except (ValueError, TypeError) as error:
            raise RuleConfigurationError(f"{path}.logic must be AND or OR") from error

        children = data.get("conditions")
        if not isinstance(children, list) or not children:
            raise RuleConfigurationError(f"{path}.conditions must be a non-empty array")
        parsed_children = []
        for index, child in enumerate(children):
            if not isinstance(child, Mapping):
                raise RuleConfigurationError(f"{path}.conditions[{index}] must be an object")
            parsed_children.append(
                parse_condition(child, path=f"{path}.conditions[{index}]")
            )
        return ConditionGroup(logic=logic, conditions=tuple(parsed_children))

    code = data.get("code")
    if not isinstance(code, str) or not code:
        raise RuleConfigurationError(f"{path}.code must be a non-empty string")
    try:
        operator = Operator(str(data["operator"]).upper())
    except (KeyError, ValueError, TypeError) as error:
        raise RuleConfigurationError(f"{path}.operator is invalid") from error

    left_data = data.get("left")
    if not isinstance(left_data, Mapping):
        raise RuleConfigurationError(f"{path}.left must be an object")

    right: Operand | None = None
    if operator not in {Operator.IS_NULL, Operator.IS_NOT_NULL}:
        right_data = data.get("right")
        if not isinstance(right_data, Mapping):
            raise RuleConfigurationError(f"{path}.right must be an object")
        right = Operand.from_dict(right_data)

    return Comparison(
        code=code,
        left=Operand.from_dict(left_data),
        operator=operator,
        right=right,
    )


def parse_rules(payload: object) -> tuple[DistributionRule, ...]:
    if isinstance(payload, Mapping):
        payload = payload.get("rules")
    if not isinstance(payload, list):
        raise RuleConfigurationError("rules cache must contain an array or {rules: [...]} object")

    rules = []
    for index, item in enumerate(payload):
        if not isinstance(item, Mapping):
            raise RuleConfigurationError(f"rules[{index}] must be an object")
        rules.append(DistributionRule.from_dict(item))

    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        raise RuleConfigurationError("rule ids must be unique")
    return tuple(sorted((rule for rule in rules if rule.enabled), key=lambda rule: (rule.priority, rule.id)))

