from __future__ import annotations

import asyncio
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from redis.asyncio import Redis

from .config import Settings
from .engine import default_rule_engine
from .redis_repository import RedisExecutorRepository
from .rules_repository import RedisRuleRepository
from .worker import RuleEngineWorker


async def main() -> None:
    settings = Settings.from_env()
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
    repository = RedisExecutorRepository(
        redis,
        online_set_key=settings.redis_online_set_key,
        executor_key_prefix=settings.redis_executor_key_prefix,
    )
    rule_repository = RedisRuleRepository(
        redis,
        rules_key=settings.redis_rules_key,
        local_ttl_seconds=settings.rules_local_ttl_seconds,
    )
    worker = RuleEngineWorker(
        settings,
        consumer,
        producer,
        repository,
        rule_repository,
        default_rule_engine(),
    )

    await consumer.start()
    await producer.start()
    try:
        await worker.run()
    finally:
        await consumer.stop()
        await producer.stop()
        await redis.aclose()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
