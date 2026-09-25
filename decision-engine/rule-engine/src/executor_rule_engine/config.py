from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    kafka_bootstrap_servers: str
    kafka_order_topic: str
    kafka_result_topic: str
    kafka_dlq_topic: str
    kafka_consumer_group: str
    kafka_client_id: str
    redis_url: str
    redis_online_set_key: str
    redis_executor_key_prefix: str
    redis_rules_key: str
    rules_local_ttl_seconds: float
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            kafka_order_topic=os.getenv("KAFKA_ORDER_TOPIC", "orders.created"),
            kafka_result_topic=os.getenv(
                "KAFKA_RESULT_TOPIC", "orders.rule-engine.completed"
            ),
            kafka_dlq_topic=os.getenv("KAFKA_DLQ_TOPIC", "orders.rule-engine.dlq"),
            kafka_consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "rule-engine-v1"),
            kafka_client_id=os.getenv("KAFKA_CLIENT_ID", "rule-engine"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            redis_online_set_key=os.getenv(
                "REDIS_ONLINE_SET_KEY", "executors:online"
            ),
            redis_executor_key_prefix=os.getenv(
                "REDIS_EXECUTOR_KEY_PREFIX", "executor:"
            ),
            redis_rules_key=os.getenv("REDIS_RULES_KEY", "rules:active"),
            rules_local_ttl_seconds=float(
                os.getenv("RULES_LOCAL_TTL_SECONDS", "5")
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
