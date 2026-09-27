"""Run the complete local decision pipeline on diverse non-IT test data."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import json
import sys
from uuid import UUID

from decision_engine import DecisionPipeline, ExecutorProfile, PipelineOrder
from decision_engine.balancer import Balancer, ExecutorLoad, InMemoryLoadRepository
from decision_engine.feature_extractor import HeuristicFeatureExtractor
from decision_engine.ml_ranker.inference import load_ranker_or_fallback
from decision_engine.publisher import InMemoryDecisionResultPublisher
from decision_engine.rule_engine.domain import ExecutorSettings, OrderStatus, OrderType
from decision_engine.rule_engine.engine import default_rule_engine


SUBJECT = UUID("89a04ed7-a821-46dc-8233-c62fb71f0d24")
NAMES = {
    "101": "\u0421\u0442\u0440\u0430\u0445\u043e\u0432\u043e\u0439 \u044d\u043a\u0441\u043f\u0435\u0440\u0442",
    "102": "\u042e\u0440\u0438\u0441\u0442",
    "103": "\u0424\u0438\u043d\u0430\u043d\u0441\u043e\u0432\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a",
    "104": "\u0421\u043c\u0435\u0442\u0447\u0438\u043a",
    "105": "\u0421\u043f\u0435\u0446\u0438\u0430\u043b\u0438\u0441\u0442 \u043a\u043b\u0438\u0435\u043d\u0442\u0441\u043a\u043e\u0433\u043e \u0441\u0435\u0440\u0432\u0438\u0441\u0430",
    "106": "\u0410\u0440\u0445\u0438\u0432\u0438\u0441\u0442",
}


def profile(
    user_id: int,
    *,
    scores: tuple[float, float, float, float],
    average_time: float,
    orders_count: int,
    capacity: float,
    skills: tuple[str, ...],
    active: bool = True,
    daily_count: int = 0,
    daily_limit: int | None = 20,
) -> ExecutorProfile:
    experience, speed, reliability, success = scores
    return ExecutorProfile(
        user_id=user_id,
        settings=ExecutorSettings(
            order_type=OrderType.ORDER_2,
            subject=SUBJECT,
            max_daily_limit=daily_limit,
        ),
        experience_score=experience,
        speed_score=speed,
        reliability_score=reliability,
        historical_success_rate=success,
        historical_avg_processing_time=average_time,
        historical_orders_count=orders_count,
        capacity=capacity,
        active=active,
        daily_count=daily_count,
        skills=skills,
    )


def candidates() -> list[ExecutorProfile]:
    return [
        profile(
            101,
            scores=(0.94, 0.55, 0.96, 0.93),
            average_time=18.0,
            orders_count=640,
            capacity=0.8,
            skills=(
                "\u043e\u0446\u0435\u043d\u043a\u0430 \u0443\u0449\u0435\u0440\u0431\u0430",
                "\u0441\u0442\u0440\u0430\u0445\u043e\u0432\u043e\u0439 \u043f\u043e\u043b\u0438\u0441",
                "\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b",
            ),
        ),
        profile(
            102,
            scores=(0.82, 0.62, 0.91, 0.89),
            average_time=14.0,
            orders_count=410,
            capacity=0.9,
            skills=(
                "\u044e\u0440\u0438\u0434\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u044d\u043a\u0441\u043f\u0435\u0440\u0442\u0438\u0437\u0430",
                "\u043f\u0440\u0435\u0442\u0435\u043d\u0437\u0438\u044f",
                "\u0437\u0430\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435",
            ),
        ),
        profile(
            103,
            scores=(0.63, 0.91, 0.84, 0.86),
            average_time=6.0,
            orders_count=230,
            capacity=1.2,
            skills=(
                "\u0440\u0430\u0441\u0447\u0435\u0442 \u0432\u044b\u043f\u043b\u0430\u0442\u044b",
                "\u043a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044f",
                "\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b",
            ),
        ),
        profile(
            104,
            scores=(0.76, 0.70, 0.88, 0.85),
            average_time=11.0,
            orders_count=175,
            capacity=0.6,
            skills=(
                "\u0437\u0430\u0442\u043e\u043f\u043b\u0435\u043d\u0438\u0435",
                "\u0441\u043c\u0435\u0442\u0430",
                "\u0440\u0435\u043c\u043e\u043d\u0442",
                "\u043e\u0446\u0435\u043d\u043a\u0430 \u0443\u0449\u0435\u0440\u0431\u0430",
            ),
        ),
        profile(
            105,
            scores=(0.58, 0.95, 0.79, 0.81),
            average_time=4.0,
            orders_count=920,
            capacity=1.4,
            skills=(
                "\u043e\u0431\u0440\u0430\u0449\u0435\u043d\u0438\u0435",
                "\u043a\u043b\u0438\u0435\u043d\u0442",
                "\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b",
            ),
            daily_count=20,
            daily_limit=20,
        ),
        profile(
            106,
            scores=(0.88, 0.48, 0.97, 0.94),
            average_time=22.0,
            orders_count=1_120,
            capacity=0.7,
            skills=(
                "\u0430\u0440\u0445\u0438\u0432",
                "\u0440\u0435\u0435\u0441\u0442\u0440",
                "\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b",
            ),
            active=False,
        ),
    ]


async def run() -> dict[str, object]:
    now = datetime.now(UTC)
    publisher = InMemoryDecisionResultPublisher()
    ranker = load_ranker_or_fallback()
    pipeline = DecisionPipeline(
        default_rule_engine(),
        HeuristicFeatureExtractor(),
        ranker,
        Balancer(
            InMemoryLoadRepository(
                {
                    "101": ExecutorLoad(
                        active_count=4,
                        active_weight=4.0,
                        pending_count=1,
                        pending_weight=0.8,
                        processed_today=12,
                        last_assignment_at=now - timedelta(minutes=4),
                    ),
                    "102": ExecutorLoad(
                        active_count=1,
                        active_weight=1.0,
                        processed_today=7,
                        last_assignment_at=now - timedelta(minutes=25),
                    ),
                    "103": ExecutorLoad(
                        active_count=1,
                        active_weight=0.5,
                        processed_today=9,
                        last_assignment_at=now - timedelta(minutes=12),
                    ),
                    "104": ExecutorLoad(
                        pending_count=1,
                        pending_weight=0.4,
                        processed_today=3,
                        last_assignment_at=now - timedelta(hours=2),
                    ),
                }
            )
        ),
        publisher,
    )
    order = PipelineOrder(
        id="CLAIM-2026-00042",
        timestamp=now,
        sum=185_000,
        order_type=OrderType.ORDER_2,
        subject=SUBJECT,
        status=OrderStatus.PROCESSED,
        vip=False,
        weight=0.8,
        text=(
            "\u0421\u0440\u043e\u0447\u043d\u043e \u043f\u0440\u043e\u0432\u0435\u0441\u0442\u0438 "
            "\u044d\u043a\u0441\u043f\u0435\u0440\u0442\u0438\u0437\u0443 \u0437\u0430\u044f\u0432\u043b\u0435\u043d\u0438\u044f "
            "\u043d\u0430 \u043a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044e \u043f\u043e\u0441\u043b\u0435 "
            "\u0437\u0430\u0442\u043e\u043f\u043b\u0435\u043d\u0438\u044f. \u041d\u0443\u0436\u043d\u044b "
            "\u043e\u0446\u0435\u043d\u043a\u0430 \u0443\u0449\u0435\u0440\u0431\u0430, \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 "
            "\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432, \u0441\u0442\u0440\u0430\u0445\u043e\u0432\u043e\u0433\u043e "
            "\u043f\u043e\u043b\u0438\u0441\u0430 \u0438 \u043f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430 "
            "\u0437\u0430\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f."
        ),
    )
    result = await pipeline.decide(order, candidates())
    rejected = {
        str(item.executor_id): [violation.code for violation in item.violations]
        for item in result.rule_result.rejected
    }
    return {
        "scenario": "\u041e\u0446\u0435\u043d\u043a\u0430 \u0437\u0430\u044f\u0432\u043b\u0435\u043d\u0438\u044f \u043d\u0430 \u043a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044e \u0443\u0449\u0435\u0440\u0431\u0430",
        "order_id": order.id,
        "ranker_model": ranker.model_version,
        "rule_engine": {
            "eligible": [
                {"executor_id": str(item), "role": NAMES[str(item)]}
                for item in result.rule_result.eligible_executor_ids
            ],
            "rejected": [
                {
                    "executor_id": executor_id,
                    "role": NAMES[executor_id],
                    "violations": violations,
                }
                for executor_id, violations in rejected.items()
            ],
        },
        "feature_extractor": result.extracted_features.as_dict(),
        "ml_ranking": [
            {**item.as_dict(), "role": NAMES[item.executor_id]}
            for item in result.ml_ranking
        ],
        "balanced_candidates": [
            {**item.as_dict(), "role": NAMES[item.executor_id]}
            for item in result.balanced_candidates
        ],
        "selected": {
            "executor_id": result.selected_executor_id,
            "role": NAMES[result.selected_executor_id]
            if result.selected_executor_id is not None
            else None,
        },
        "published_event": publisher.events[0],
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
