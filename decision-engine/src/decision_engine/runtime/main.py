from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from redis.asyncio import Redis

from ..balancer import Balancer, RedisHashLoadRepository
from ..feature_extractor import HeuristicFeatureExtractor, MLFeatureExtractor
from ..ml_ranker.inference import load_ranker_or_fallback
from ..pipeline import DecisionPipeline
from ..publisher import KafkaDecisionResultPublisher
from ..rule_engine.engine import integration_rule_engine
from ..rule_engine.rules_repository import RedisRuleRepository
from .config import RuntimeSettings
from .repository import RedisExecutorProfileRepository
from .worker import DecisionEngineWorker


async def main() -> None:
    settings = RuntimeSettings.from_env()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    consumer = AIOKafkaConsumer(
        settings.kafka_order_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        client_id=settings.kafka_client_id,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.kafka_client_id,
    )
    pipeline = DecisionPipeline(
        integration_rule_engine(),
        _build_feature_extractor(settings),
        load_ranker_or_fallback(
            Path(settings.model_root) / "ranker-v2.cbm",
            Path(settings.model_root) / "ranker-v2.metadata.json",
        ),
        Balancer(
            RedisHashLoadRepository(
                redis, key_prefix=settings.redis_executor_key_prefix
            )
        ),
        KafkaDecisionResultPublisher(
            producer, topic=settings.kafka_decision_topic
        ),
    )
    worker = DecisionEngineWorker(
        settings,
        consumer,
        producer,
        RedisExecutorProfileRepository(
            redis,
            active_set_key=settings.redis_active_set_key,
            executor_key_prefix=settings.redis_executor_key_prefix,
        ),
        RedisRuleRepository(
            redis,
            rules_key=settings.redis_rules_key,
            local_ttl_seconds=settings.rules_local_ttl_seconds,
        ),
        pipeline,
    )

    await consumer.start()
    await producer.start()
    try:
        await worker.run()
    finally:
        await consumer.stop()
        await producer.stop()
        await redis.aclose()


def _build_feature_extractor(settings: RuntimeSettings):
    if settings.feature_extractor_mode == "ml":
        model_root = Path(settings.model_root) / "feature-extractor"
        return MLFeatureExtractor.from_local_models(
            classifier_dir=model_root / "classifier" / "best",
            embedding_model_dir=(
                model_root
                / "matching"
                / "paraphrase-multilingual-MiniLM-L12-v2"
            ),
            device=settings.feature_extractor_device
        )
    if settings.feature_extractor_mode == "heuristic":
        logging.getLogger(__name__).warning(
            "using heuristic feature extractor by explicit configuration"
        )
        return HeuristicFeatureExtractor()
    raise ValueError(
        "FEATURE_EXTRACTOR_MODE must be either 'ml' or 'heuristic'"
    )


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()

