import json
from pathlib import Path
from uuid import UUID

import pytest

from executor_rule_engine.domain import Executor, ExecutorSettings, Order, OrderStatus, OrderType
from executor_rule_engine.dynamic_rules import (
    DistributionRule,
    Operator,
    RuleConfigurationError,
    parse_rules,
)
from executor_rule_engine.engine import default_rule_engine
from executor_rule_engine.field_registry import DEFAULT_FIELD_REGISTRY
from executor_rule_engine.rule_evaluator import compare


SUBJECT = UUID("96bc9564-fb0b-4db5-b4b6-ce11c2fb5e6f")


def make_order(**overrides: object) -> Order:
    values = {
        "id": 42,
        "sum": 1_000,
        "client_msp": "client-a",
        "executor_msp": "executor-a",
        "order_type": OrderType.ORDER_1,
        "subject": SUBJECT,
        "vip": False,
        "status": OrderStatus.PROCESSED,
    }
    values.update(overrides)
    return Order(**values)  # type: ignore[arg-type]


def make_executor(**overrides: object) -> Executor:
    settings = {
        "order_type": OrderType.ORDER_1,
        "subject": SUBJECT,
        "min_accept_sum": 500,
        "max_accept_sum": 2_000,
        "client_msp": "client-a",
        "executor_msp": "executor-a",
        "vip": False,
        "max_daily_limit": 10,
    }
    settings.update(overrides)
    return Executor(
        user_id=101,
        active=True,
        daily_count=1,
        settings=ExecutorSettings(**settings),  # type: ignore[arg-type]
    )


def load_example_rules():
    path = Path(__file__).parents[1] / "examples" / "rules.json"
    return parse_rules(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    ("left", "operator", "right", "expected"),
    [
        (2, Operator.EQ, 2, True),
        (2, Operator.NEQ, 3, True),
        (3, Operator.GT, 2, True),
        (3, Operator.GTE, 3, True),
        (2, Operator.LT, 3, True),
        (2, Operator.LTE, 2, True),
        ("ORDER_2", Operator.IN, ["ORDER_1", "ORDER_2"], True),
        ("ORDER_3", Operator.NOT_IN, ["ORDER_1", "ORDER_2"], True),
        (5, Operator.BETWEEN, [1, 5], True),
        (["a", "b"], Operator.CONTAINS, "b", True),
        (["a", "b"], Operator.NOT_CONTAINS, "c", True),
        (None, Operator.IS_NULL, None, True),
        (0, Operator.IS_NOT_NULL, None, True),
    ],
)
def test_mvp_operators(left, operator, right, expected) -> None:
    assert compare(left, operator, right) is expected


def test_nested_groups_and_decision_trace() -> None:
    rule = DistributionRule.from_dict(
        {
            "id": "vip_type",
            "name": "VIP and supported type",
            "version": 3,
            "priority": 7,
            "condition": {
                "logic": "AND",
                "conditions": [
                    {
                        "code": "VIP",
                        "left": {"source": "order", "field": "vip"},
                        "operator": "EQ",
                        "right": {"source": "constant", "value": True},
                    },
                    {
                        "logic": "OR",
                        "conditions": [
                            {
                                "code": "TYPE_1",
                                "left": {"source": "order", "field": "order_type"},
                                "operator": "EQ",
                                "right": {"source": "constant", "value": "ORDER_1"},
                            },
                            {
                                "code": "TYPE_2",
                                "left": {"source": "order", "field": "order_type"},
                                "operator": "EQ",
                                "right": {"source": "constant", "value": "ORDER_2"},
                            },
                        ],
                    },
                ],
            },
        }
    )

    result = default_rule_engine().filter(
        make_order(vip=True), [make_executor(vip=True)], [rule]
    )
    trace = result.decisions[0].trace_dict()

    assert result.eligible_executor_ids == [101]
    assert trace["rule_traces"][0]["rule_version"] == 3
    assert [item["condition"] for item in trace["rule_traces"][0]["conditions"]] == [
        "VIP",
        "TYPE_1",
        "TYPE_2",
    ]


def test_rules_are_sorted_and_disabled_rules_are_ignored() -> None:
    rules = parse_rules(
        [
            {
                "id": "later",
                "name": "later",
                "priority": 200,
                "condition": {
                    "code": "LATER",
                    "left": {"source": "constant", "value": True},
                    "operator": "EQ",
                    "right": {"source": "constant", "value": True},
                },
            },
            {
                "id": "disabled",
                "name": "disabled",
                "enabled": False,
                "priority": 1,
                "condition": {
                    "code": "DISABLED",
                    "left": {"source": "constant", "value": False},
                    "operator": "EQ",
                    "right": {"source": "constant", "value": True},
                },
            },
            {
                "id": "first",
                "name": "first",
                "priority": 10,
                "condition": {
                    "code": "FIRST",
                    "left": {"source": "constant", "value": True},
                    "operator": "EQ",
                    "right": {"source": "constant", "value": True},
                },
            },
        ]
    )

    assert [rule.id for rule in rules] == ["first", "later"]


def test_example_rules_reject_mismatching_executor_with_explanation() -> None:
    result = default_rule_engine().filter(
        make_order(sum=3_000, vip=True),
        [make_executor(max_accept_sum=2_000, vip=False)],
        load_example_rules(),
    )
    decision = result.decisions[0]

    assert decision.eligible is False
    assert {violation.code for violation in decision.violations} == {
        "accepted_amount",
        "vip",
    }
    failed_codes = {
        item["condition"] for item in decision.trace_dict()["failed_conditions"]
    }
    assert {"MAX_SUM", "VIP_ALLOWED"} <= failed_codes


def test_unknown_field_is_rejected_fail_closed() -> None:
    rule = DistributionRule.from_dict(
        {
            "id": "bad",
            "name": "bad",
            "condition": {
                "code": "BAD",
                "left": {"source": "order", "field": "password"},
                "operator": "EQ",
                "right": {"source": "constant", "value": "secret"},
            },
        }
    )

    with pytest.raises(RuleConfigurationError, match="unknown field"):
        default_rule_engine().filter(make_order(), [make_executor()], [rule])


def test_field_registry_is_serializable_for_backend_api() -> None:
    fields = DEFAULT_FIELD_REGISTRY.public_dict()

    assert fields["order"]
    assert fields["executor"]
    assert next(item for item in fields["order"] if item["field"] == "sum") == {
        "field": "sum",
        "label": "Сумма заявки",
        "type": "number",
        "operators": [
            "EQ",
            "NEQ",
            "GT",
            "GTE",
            "LT",
            "LTE",
            "BETWEEN",
            "IS_NULL",
            "IS_NOT_NULL",
        ],
    }


def test_invalid_between_operand_is_rejected() -> None:
    with pytest.raises(RuleConfigurationError, match="two-item"):
        compare(5, Operator.BETWEEN, [1])
