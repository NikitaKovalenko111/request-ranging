from __future__ import annotations

from collections.abc import Iterable, Sequence

from .domain import CandidateDecision, Executor, FilterResult, Order, RuleViolation
from .dynamic_rules import DistributionRule
from .rule_evaluator import DynamicRuleEvaluator
from .rules import DEFAULT_RULES, INTEGRATION_RULES, Rule


class RuleEngine:
    def __init__(
        self,
        rules: Sequence[Rule],
        *,
        collect_all_violations: bool = True,
        dynamic_evaluator: DynamicRuleEvaluator | None = None,
    ):
        self._rules = tuple(rules)
        self._collect_all_violations = collect_all_violations
        self._dynamic_evaluator = dynamic_evaluator or DynamicRuleEvaluator()

    def filter(
        self,
        order: Order,
        executors: Iterable[Executor],
        dynamic_rules: Iterable[DistributionRule] = (),
    ) -> FilterResult:
        decisions: list[CandidateDecision] = []
        ordered_dynamic_rules = sorted(
            (rule for rule in dynamic_rules if rule.enabled),
            key=lambda rule: (rule.priority, rule.id),
        )

        for executor in executors:
            violations = []
            traces = []
            for rule in self._rules:
                violation = rule.evaluate(order, executor)
                if violation is not None:
                    violations.append(violation)
                    if not self._collect_all_violations:
                        break

            if not violations:
                for rule in ordered_dynamic_rules:
                    trace = self._dynamic_evaluator.evaluate(rule, order, executor)
                    traces.append(trace)
                    if not trace.result:
                        violations.append(
                            RuleViolation(
                                code=rule.id,
                                message=f'dynamic rule failed: {rule.name}',
                                details={
                                    'rule_id': rule.id,
                                    'rule_version': rule.version,
                                    'failed_conditions': [
                                        item.as_dict()
                                        for item in trace.conditions
                                        if not item.result
                                    ],
                                },
                            )
                        )
                        if not self._collect_all_violations:
                            break

            decisions.append(
                CandidateDecision(
                    executor_id=executor.user_id,
                    eligible=not violations,
                    violations=tuple(violations),
                    traces=tuple(traces),
                )
            )

        return FilterResult(order_id=order.id, decisions=tuple(decisions))


def default_rule_engine(*, collect_all_violations: bool = True) -> RuleEngine:
    return RuleEngine(DEFAULT_RULES, collect_all_violations=collect_all_violations)


def integration_rule_engine(*, collect_all_violations: bool = True) -> RuleEngine:
    return RuleEngine(INTEGRATION_RULES, collect_all_violations=collect_all_violations)
