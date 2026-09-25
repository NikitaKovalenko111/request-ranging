from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import Executor, Order
from .dynamic_rules import (
    Comparison,
    Condition,
    ConditionGroup,
    DistributionRule,
    GroupLogic,
    Operand,
    OperandSource,
    Operator,
    RuleConfigurationError,
)
from .field_registry import DEFAULT_FIELD_REGISTRY, FieldRegistry


@dataclass(frozen=True, slots=True)
class ConditionTrace:
    rule_id: str
    rule_version: int
    condition: str
    left_value: Any
    operator: str
    right_value: Any
    result: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "condition": self.condition,
            "left_value": self.left_value,
            "operator": self.operator,
            "right_value": self.right_value,
            "result": self.result,
        }


@dataclass(frozen=True, slots=True)
class DynamicRuleEvaluation:
    rule_id: str
    rule_name: str
    rule_version: int
    priority: int
    result: bool
    conditions: tuple[ConditionTrace, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_version": self.rule_version,
            "priority": self.priority,
            "result": self.result,
            "conditions": [condition.as_dict() for condition in self.conditions],
        }


class DynamicRuleEvaluator:
    def __init__(self, registry: FieldRegistry = DEFAULT_FIELD_REGISTRY) -> None:
        self._registry = registry

    def evaluate(
        self, rule: DistributionRule, order: Order, executor: Executor
    ) -> DynamicRuleEvaluation:
        result, traces = self._evaluate_condition(rule, rule.condition, order, executor)
        return DynamicRuleEvaluation(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_version=rule.version,
            priority=rule.priority,
            result=result,
            conditions=tuple(traces),
        )

    def _evaluate_condition(
        self,
        rule: DistributionRule,
        condition: Condition,
        order: Order,
        executor: Executor,
    ) -> tuple[bool, list[ConditionTrace]]:
        if isinstance(condition, ConditionGroup):
            results: list[bool] = []
            traces: list[ConditionTrace] = []
            for child in condition.conditions:
                child_result, child_traces = self._evaluate_condition(
                    rule, child, order, executor
                )
                results.append(child_result)
                traces.extend(child_traces)
            result = all(results) if condition.logic is GroupLogic.AND else any(results)
            return result, traces

        left = self._resolve(condition.left, order, executor)
        right = (
            self._resolve(condition.right, order, executor)
            if condition.right is not None
            else None
        )
        self._validate_field_operator(condition)
        result = compare(left, condition.operator, right)
        return result, [
            ConditionTrace(
                rule_id=rule.id,
                rule_version=rule.version,
                condition=condition.code,
                left_value=left,
                operator=condition.operator.value,
                right_value=right,
                result=result,
            )
        ]

    def _resolve(self, operand: Operand, order: Order, executor: Executor) -> Any:
        if operand.source is OperandSource.CONSTANT:
            return operand.value
        assert operand.field is not None
        entity = order if operand.source is OperandSource.ORDER else executor
        return self._registry.resolve(operand.source, operand.field, entity)

    def _validate_field_operator(self, comparison: Comparison) -> None:
        if comparison.left.source is not OperandSource.CONSTANT:
            assert comparison.left.field is not None
            self._registry.validate_operator(
                comparison.left.source, comparison.left.field, comparison.operator
            )


def compare(left: Any, operator: Operator, right: Any = None) -> bool:
    if operator is Operator.IS_NULL:
        return left is None
    if operator is Operator.IS_NOT_NULL:
        return left is not None
    if operator is Operator.EQ:
        return left == right
    if operator is Operator.NEQ:
        return left != right

    if left is None or right is None:
        return False

    try:
        if operator is Operator.GT:
            return left > right
        if operator is Operator.GTE:
            return left >= right
        if operator is Operator.LT:
            return left < right
        if operator is Operator.LTE:
            return left <= right
        if operator is Operator.IN:
            return left in right
        if operator is Operator.NOT_IN:
            return left not in right
        if operator is Operator.BETWEEN:
            if not isinstance(right, (list, tuple)) or len(right) != 2:
                raise RuleConfigurationError("BETWEEN requires a two-item right operand")
            return right[0] <= left <= right[1]
        if operator is Operator.CONTAINS:
            return right in left
        if operator is Operator.NOT_CONTAINS:
            return right not in left
    except TypeError as error:
        raise RuleConfigurationError(
            f"operator {operator.value} cannot compare {type(left).__name__} and {type(right).__name__}"
        ) from error

    raise RuleConfigurationError(f"unsupported operator: {operator.value}")

