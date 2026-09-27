from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Iterable, Sequence
from uuid import UUID

from .balancer import Balancer, BalancerCandidate, BalancerOrder, BalancedCandidate
from .feature_extractor import (
    ExtractedFeatures,
    FeatureCandidate,
    FeatureExtractionRequest,
    FeatureExtractor,
)
from .ml_ranker.inference import Ranker
from .ml_ranker.schemas import Executor as RankerExecutor
from .ml_ranker.schemas import Order as RankerOrder
from .ml_ranker.schemas import RankedExecutor
from .rule_engine.domain import Executor as RuleExecutor
from .rule_engine.domain import ExecutorSettings, FilterResult
from .rule_engine.domain import Order as RuleOrder
from .rule_engine.domain import OrderStatus, OrderType
from .rule_engine.dynamic_rules import DistributionRule
from .rule_engine.engine import RuleEngine


@dataclass(frozen=True, slots=True)
class PipelineOrder:
    '''One order contract shared by all four pipeline stages.'''

    id: int
    timestamp: datetime
    sum: int
    order_type: OrderType
    subject: UUID
    status: OrderStatus
    complexity: float | None = None
    urgency: float | None = None
    weight: float = 1.0
    parent_id: int | None = None
    user_id: int | None = None
    client_msp: str | None = None
    executor_msp: str | None = None
    vip: bool = False
    text: str | None = None

    def __post_init__(self) -> None:
        for name, value in (('complexity', self.complexity), ('urgency', self.urgency)):
            if value is not None and (not isfinite(value) or not 0.0 <= value <= 1.0):
                raise ValueError(f'{name} must be in [0, 1]')
        if not isfinite(self.weight) or self.weight <= 0:
            raise ValueError('weight must be finite and positive')

    def as_rule_order(self) -> RuleOrder:
        return RuleOrder(
            id=self.id,
            sum=self.sum,
            order_type=self.order_type,
            subject=self.subject,
            status=self.status,
            parent_id=self.parent_id,
            user_id=self.user_id,
            client_msp=self.client_msp,
            executor_msp=self.executor_msp,
            vip=self.vip,
            text=self.text,
        )

    def as_ranker_order(self, features: ExtractedFeatures) -> RankerOrder:
        return RankerOrder(
            id=str(self.id),
            timestamp=self.timestamp,
            complexity=features.complexity,
            urgency=features.urgency,
        )


@dataclass(frozen=True, slots=True)
class ExecutorProfile:
    '''Rule settings, ranking features and capacity for one executor.'''

    user_id: int
    settings: ExecutorSettings
    experience_score: float
    speed_score: float
    reliability_score: float
    historical_success_rate: float
    historical_avg_processing_time: float
    historical_orders_count: int
    capacity: float = 1.0
    active: bool = True
    daily_count: int = 0
    skills: tuple[str, ...] = ()

    def as_rule_executor(self) -> RuleExecutor:
        return RuleExecutor(
            user_id=self.user_id,
            settings=self.settings,
            active=self.active,
            daily_count=self.daily_count,
        )

    def as_ranker_executor(self) -> RankerExecutor:
        return RankerExecutor(
            id=str(self.user_id),
            experience_score=self.experience_score,
            speed_score=self.speed_score,
            reliability_score=self.reliability_score,
            historical_success_rate=self.historical_success_rate,
            historical_avg_processing_time=self.historical_avg_processing_time,
            historical_orders_count=self.historical_orders_count,
        )


@dataclass(frozen=True, slots=True)
class PipelineResult:
    order_id: int
    rule_result: FilterResult
    extracted_features: ExtractedFeatures
    ml_ranking: tuple[RankedExecutor, ...]
    balanced_candidates: tuple[BalancedCandidate, ...]

    @property
    def selected_executor_id(self) -> str | None:
        if not self.balanced_candidates:
            return None
        return self.balanced_candidates[0].executor_id

    def as_dict(self) -> dict[str, Any]:
        return {
            'order_id': self.order_id,
            'selected_executor_id': self.selected_executor_id,
            'rule_engine': self.rule_result.as_dict(),
            'feature_extractor': self.extracted_features.as_dict(),
            'ml_ranking': [item.as_dict() for item in self.ml_ranking],
            'balanced_candidates': [item.as_dict() for item in self.balanced_candidates],
        }


class DecisionPipeline:
    '''Runs Rule Engine -> Feature Extractor -> ML Ranker -> Balancer.'''

    def __init__(
        self,
        rule_engine: RuleEngine,
        feature_extractor: FeatureExtractor,
        ranker: Ranker,
        balancer: Balancer,
    ) -> None:
        self._rule_engine = rule_engine
        self._feature_extractor = feature_extractor
        self._ranker = ranker
        self._balancer = balancer

    async def decide(
        self,
        order: PipelineOrder,
        executors: Sequence[ExecutorProfile],
        dynamic_rules: Iterable[DistributionRule] = (),
    ) -> PipelineResult:
        profiles = self._index_profiles(executors)
        rule_result = self._rule_engine.filter(
            order.as_rule_order(),
            (profile.as_rule_executor() for profile in executors),
            dynamic_rules,
        )
        eligible = [profiles[executor_id] for executor_id in rule_result.eligible_executor_ids]
        extracted_features = self._feature_extractor.extract(
            FeatureExtractionRequest(
                order_id=str(order.id),
                text=order.text or '',
                fallback_complexity=order.complexity,
                fallback_urgency=order.urgency,
                candidates=tuple(
                    FeatureCandidate(
                        executor_id=str(profile.user_id),
                        skills=profile.skills,
                    )
                    for profile in eligible
                ),
            )
        )
        ml_ranking = self._ranker.rank(
            order.as_ranker_order(extracted_features),
            [profile.as_ranker_executor() for profile in eligible],
        )
        candidates = [
            BalancerCandidate(
                executor_id=item.executor_id,
                ml_score=item.score,
                capacity=profiles[int(item.executor_id)].capacity,
            )
            for item in ml_ranking
        ]
        balanced = await self._balancer.balance(
            BalancerOrder(order_id=str(order.id), weight=order.weight),
            candidates,
        )
        return PipelineResult(
            order_id=order.id,
            rule_result=rule_result,
            extracted_features=extracted_features,
            ml_ranking=tuple(ml_ranking),
            balanced_candidates=tuple(balanced),
        )

    @staticmethod
    def _index_profiles(executors: Sequence[ExecutorProfile]) -> dict[int, ExecutorProfile]:
        profiles = {executor.user_id: executor for executor in executors}
        if len(profiles) != len(executors):
            raise ValueError('executor user_ids must be unique within an order')
        return profiles
