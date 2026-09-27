from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Any, Callable
from uuid import UUID

from .domain import Executor, Order
from .dynamic_rules import OperandSource, Operator, RuleConfigurationError


class FieldType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    STRING_ARRAY = "string_array"
    NUMBER_ARRAY = "number_array"
    DATE = "date"
    DATETIME = "datetime"


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    source: OperandSource
    field: str
    type: FieldType
    label: str
    operators: tuple[Operator, ...]
    accessor: Callable[[Order | Executor], Any]

    def public_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "label": self.label,
            "type": self.type.value,
            "operators": [operator.value for operator in self.operators],
        }


class FieldRegistry:
    def __init__(self, fields: tuple[FieldDefinition, ...]) -> None:
        self._fields = {(item.source, item.field): item for item in fields}
        if len(self._fields) != len(fields):
            raise ValueError("field registry contains duplicates")

    def resolve(self, source: OperandSource, field: str, entity: Order | Executor) -> Any:
        definition = self._fields.get((source, field))
        if definition is None:
            raise RuleConfigurationError(f"unknown field: {source.value}.{field}")
        return _json_value(definition.accessor(entity))

    def validate_operator(self, source: OperandSource, field: str, operator: Operator) -> None:
        definition = self._fields.get((source, field))
        if definition is None:
            raise RuleConfigurationError(f"unknown field: {source.value}.{field}")
        if operator not in definition.operators:
            raise RuleConfigurationError(
                f"operator {operator.value} is not allowed for {source.value}.{field}"
            )

    def public_dict(self) -> dict[str, list[dict[str, Any]]]:
        result = {OperandSource.ORDER.value: [], OperandSource.EXECUTOR.value: []}
        for definition in self._fields.values():
            result[definition.source.value].append(definition.public_dict())
        for definitions in result.values():
            definitions.sort(key=lambda item: item["field"])
        return result


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


NUMBER_OPERATORS = (
    Operator.EQ,
    Operator.NEQ,
    Operator.GT,
    Operator.GTE,
    Operator.LT,
    Operator.LTE,
    Operator.BETWEEN,
    Operator.IS_NULL,
    Operator.IS_NOT_NULL,
)
STRING_OPERATORS = (
    Operator.EQ,
    Operator.NEQ,
    Operator.IN,
    Operator.NOT_IN,
    Operator.CONTAINS,
    Operator.NOT_CONTAINS,
    Operator.IS_NULL,
    Operator.IS_NOT_NULL,
)
BOOLEAN_OPERATORS = (Operator.EQ, Operator.NEQ, Operator.IS_NULL, Operator.IS_NOT_NULL)
ARRAY_OPERATORS = (
    Operator.CONTAINS,
    Operator.NOT_CONTAINS,
    Operator.EQ,
    Operator.NEQ,
    Operator.IS_NULL,
    Operator.IS_NOT_NULL,
)


DEFAULT_FIELD_REGISTRY = FieldRegistry(
    (
        FieldDefinition(OperandSource.ORDER, "id", FieldType.NUMBER, "ID заявки", NUMBER_OPERATORS, lambda item: item.id),
        FieldDefinition(OperandSource.ORDER, "parent_id", FieldType.NUMBER, "ID родительской заявки", NUMBER_OPERATORS, lambda item: item.parent_id),
        FieldDefinition(OperandSource.ORDER, "user_id", FieldType.NUMBER, "ID пользователя", NUMBER_OPERATORS, lambda item: item.user_id),
        FieldDefinition(OperandSource.ORDER, "sum", FieldType.NUMBER, "Сумма заявки", NUMBER_OPERATORS, lambda item: item.sum),
        FieldDefinition(OperandSource.ORDER, "client_msp", FieldType.STRING, "МСП клиента", STRING_OPERATORS, lambda item: item.client_msp),
        FieldDefinition(OperandSource.ORDER, "executor_msp", FieldType.STRING, "МСП исполнителя", STRING_OPERATORS, lambda item: item.executor_msp),
        FieldDefinition(OperandSource.ORDER, "order_type", FieldType.STRING, "Тип заявки", STRING_OPERATORS, lambda item: item.order_type),
        FieldDefinition(OperandSource.ORDER, "subject", FieldType.STRING, "Тематика", STRING_OPERATORS, lambda item: item.subject),
        FieldDefinition(OperandSource.ORDER, "vip", FieldType.BOOLEAN, "VIP", BOOLEAN_OPERATORS, lambda item: item.vip),
        FieldDefinition(OperandSource.ORDER, "status", FieldType.STRING, "Статус заявки", STRING_OPERATORS, lambda item: item.status),
        FieldDefinition(OperandSource.EXECUTOR, "user_id", FieldType.NUMBER, "ID исполнителя", NUMBER_OPERATORS, lambda item: item.user_id),
        FieldDefinition(OperandSource.EXECUTOR, "active", FieldType.BOOLEAN, "Активен", BOOLEAN_OPERATORS, lambda item: item.active),
        FieldDefinition(OperandSource.EXECUTOR, "daily_count", FieldType.NUMBER, "Заявок за сутки", NUMBER_OPERATORS, lambda item: item.daily_count),
        FieldDefinition(OperandSource.EXECUTOR, "min_accept_sum", FieldType.NUMBER, "Минимальная сумма", NUMBER_OPERATORS, lambda item: item.settings.min_accept_sum),
        FieldDefinition(OperandSource.EXECUTOR, "max_accept_sum", FieldType.NUMBER, "Максимальная сумма", NUMBER_OPERATORS, lambda item: item.settings.max_accept_sum),
        FieldDefinition(OperandSource.EXECUTOR, "min_reject_sum", FieldType.NUMBER, "Минимальная сумма отказа", NUMBER_OPERATORS, lambda item: item.settings.min_reject_sum),
        FieldDefinition(OperandSource.EXECUTOR, "max_reject_sum", FieldType.NUMBER, "Максимальная сумма отказа", NUMBER_OPERATORS, lambda item: item.settings.max_reject_sum),
        FieldDefinition(OperandSource.EXECUTOR, "client_msp", FieldType.STRING, "МСП клиента исполнителя", STRING_OPERATORS, lambda item: item.settings.client_msp),
        FieldDefinition(OperandSource.EXECUTOR, "executor_msp", FieldType.STRING, "МСП исполнителя", STRING_OPERATORS, lambda item: item.settings.executor_msp),
        FieldDefinition(OperandSource.EXECUTOR, "order_type", FieldType.STRING, "Тип заявки исполнителя", STRING_OPERATORS, lambda item: item.settings.order_type),
        FieldDefinition(OperandSource.EXECUTOR, "allowed_order_types", FieldType.STRING_ARRAY, "Допустимые типы заявок", ARRAY_OPERATORS, lambda item: (item.settings.order_type,)),
        FieldDefinition(OperandSource.EXECUTOR, "subject", FieldType.STRING, "Тематика исполнителя", STRING_OPERATORS, lambda item: item.settings.subject),
        FieldDefinition(OperandSource.EXECUTOR, "subjects", FieldType.STRING_ARRAY, "Тематики исполнителя", ARRAY_OPERATORS, lambda item: () if item.settings.subject is None else (item.settings.subject,)),
        FieldDefinition(OperandSource.EXECUTOR, "vip", FieldType.BOOLEAN, "VIP-допуск", BOOLEAN_OPERATORS, lambda item: item.settings.vip),
        FieldDefinition(OperandSource.EXECUTOR, "vip_allowed", FieldType.BOOLEAN, "VIP-допуск", BOOLEAN_OPERATORS, lambda item: item.settings.vip),
        FieldDefinition(OperandSource.EXECUTOR, "max_daily_limit", FieldType.NUMBER, "Суточный лимит", NUMBER_OPERATORS, lambda item: item.settings.max_daily_limit),
    )
)
