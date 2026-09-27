from datetime import UTC, datetime
from uuid import UUID

import pytest

from decision_engine import DecisionPipeline, ExecutorProfile, PipelineOrder
from decision_engine.balancer import Balancer, ExecutorLoad, InMemoryLoadRepository
from decision_engine.feature_extractor import HeuristicFeatureExtractor
from decision_engine.ml_ranker.inference import HeuristicRanker
from decision_engine.rule_engine.domain import ExecutorSettings, OrderStatus, OrderType
from decision_engine.rule_engine.engine import default_rule_engine


def profile(user_id: int, experience: float, *, active: bool = True) -> ExecutorProfile:
    return ExecutorProfile(
        user_id=user_id,
        settings=ExecutorSettings(order_type=OrderType.ORDER_1),
        experience_score=experience,
        speed_score=experience,
        reliability_score=experience,
        historical_success_rate=experience,
        historical_avg_processing_time=10.0,
        historical_orders_count=100,
        active=active,
        skills=('python', 'postgresql'),
    )


@pytest.mark.asyncio
async def test_pipeline_filters_ranks_and_balances() -> None:
    pipeline = DecisionPipeline(
        default_rule_engine(),
        HeuristicFeatureExtractor(),
        HeuristicRanker(),
        Balancer(
            InMemoryLoadRepository(
                {
                    '1': ExecutorLoad(active_count=3, active_weight=3.0),
                    '2': ExecutorLoad(),
                }
            )
        ),
    )
    order = PipelineOrder(
        id=101,
        timestamp=datetime.now(UTC),
        sum=50_000,
        order_type=OrderType.ORDER_1,
        subject=UUID('00000000-0000-0000-0000-000000000001'),
        status=OrderStatus.PROCESSED,
        complexity=0.8,
        urgency=0.7,
    )

    result = await pipeline.decide(
        order,
        [
            profile(1, 0.95),
            profile(2, 0.70),
            profile(3, 0.99, active=False),
        ],
    )

    assert result.rule_result.eligible_executor_ids == [1, 2]
    assert set(result.extracted_features.skill_match_scores) == {'1', '2'}
    assert [item.executor_id for item in result.ml_ranking] == ['1', '2']
    assert [item.executor_id for item in result.balanced_candidates] == ['2', '1']
    assert result.selected_executor_id == '2'


@pytest.mark.asyncio
async def test_pipeline_handles_no_eligible_executors() -> None:
    pipeline = DecisionPipeline(
        default_rule_engine(),
        HeuristicFeatureExtractor(),
        HeuristicRanker(),
        Balancer(InMemoryLoadRepository()),
    )
    order = PipelineOrder(
        id=102,
        timestamp=datetime.now(UTC),
        sum=1,
        order_type=OrderType.ORDER_1,
        subject=UUID('00000000-0000-0000-0000-000000000001'),
        status=OrderStatus.PROCESSED,
        complexity=0.1,
        urgency=0.1,
    )

    result = await pipeline.decide(order, [profile(1, 0.5, active=False)])

    assert result.selected_executor_id is None
    assert result.ml_ranking == ()
    assert result.balanced_candidates == ()


@pytest.mark.asyncio
async def test_pipeline_extracts_ranker_order_features_from_text() -> None:
    pipeline = DecisionPipeline(
        default_rule_engine(),
        HeuristicFeatureExtractor(),
        HeuristicRanker(),
        Balancer(InMemoryLoadRepository()),
    )
    order = PipelineOrder(
        id=103,
        timestamp=datetime.now(UTC),
        sum=1,
        order_type=OrderType.ORDER_1,
        subject=UUID('00000000-0000-0000-0000-000000000001'),
        status=OrderStatus.PROCESSED,
        text=(
            '\u0421\u0440\u043e\u0447\u043d\u043e \u043d\u0443\u0436\u043d\u0430 '
            '\u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f, '
            '\u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044f \u0438 '
            '\u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u0430 '
            'Python PostgreSQL'
        ),
    )

    result = await pipeline.decide(order, [profile(1, 0.7)])

    assert result.extracted_features.urgency > 0.5
    assert result.extracted_features.complexity > 0.5
    assert result.extracted_features.language == 'ru'
    assert result.extracted_features.skill_match_scores['1'] > 0.0
