from uuid import UUID

from executor_rule_engine.domain import Executor, ExecutorSettings, Order, OrderStatus, OrderType
from executor_rule_engine.engine import RuleEngine, default_rule_engine


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


def make_executor(user_id: int = 1, **settings_overrides: object) -> Executor:
    values = {
        "min_accept_sum": 100,
        "max_accept_sum": 5_000,
        "client_msp": "client-a",
        "executor_msp": "executor-a",
        "order_type": OrderType.ORDER_1,
        "subject": SUBJECT,
        "vip": False,
        "max_daily_limit": 10,
    }
    values.update(settings_overrides)
    return Executor(
        user_id=user_id,
        active=True,
        daily_count=2,
        settings=ExecutorSettings(**values),  # type: ignore[arg-type]
    )


def test_matching_executor_is_eligible() -> None:
    result = default_rule_engine().filter(make_order(), [make_executor()])

    assert result.eligible_executor_ids == [1]
    assert result.rejected == []


def test_all_rejection_reasons_are_returned() -> None:
    executor = Executor(
        user_id=7,
        active=False,
        daily_count=10,
        settings=ExecutorSettings(
            min_accept_sum=2_000,
            order_type=OrderType.ORDER_2,
            subject=UUID("23f1f076-2894-420d-b9a4-290006d9a480"),
            vip=False,
            max_daily_limit=10,
        ),
    )

    decision = default_rule_engine().filter(
        make_order(vip=True), [executor]
    ).decisions[0]

    assert decision.eligible is False
    assert {violation.code for violation in decision.violations} == {
        "executor_active",
        "daily_limit",
    }


def test_reject_range_is_inclusive() -> None:
    import json
    from pathlib import Path

    from executor_rule_engine.dynamic_rules import parse_rules

    executor = make_executor(min_reject_sum=500, max_reject_sum=1_000)
    rules_path = Path(__file__).parents[1] / "examples" / "rules.json"
    rules = parse_rules(json.loads(rules_path.read_text(encoding="utf-8")))

    decision = default_rule_engine().filter(
        make_order(sum=1_000), [executor], rules
    ).decisions[0]

    assert decision.eligible is False
    assert [violation.code for violation in decision.violations] == [
        "rejected_amount"
    ]


def test_null_daily_limit_means_unlimited() -> None:
    executor = Executor(
        user_id=3,
        active=True,
        daily_count=99_999,
        settings=make_executor(max_daily_limit=None).settings,
    )

    result = default_rule_engine().filter(make_order(), [executor])

    assert result.eligible_executor_ids == [3]


def test_order_type_alias_from_database_is_normalized() -> None:
    order = Order.from_dict(
        {
            "id": 1,
            "sum": 500,
            "order_type": "ORDER_1",
            "subject": str(SUBJECT),
            "status": "processed",
        }
    )
    executor = Executor.from_dict(
        {
            "user_id": 4,
            "settings": {
                "order_type": "ORDER_TYPE_1",
                "subject": str(SUBJECT),
            },
        }
    )

    assert default_rule_engine().filter(order, [executor]).eligible_executor_ids == [4]


def test_new_rule_can_be_added_without_changing_engine() -> None:
    class RejectEverythingRule:
        code = "custom"

        def evaluate(self, order: Order, executor: Executor):
            from executor_rule_engine.domain import RuleViolation

            return RuleViolation(self.code, "custom rejection")

    result = RuleEngine([RejectEverythingRule()]).filter(
        make_order(), [make_executor()]
    )

    assert result.decisions[0].violations[0].code == "custom"
