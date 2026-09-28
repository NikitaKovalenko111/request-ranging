from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    kafka_bootstrap_servers: str
    kafka_order_topic: str
    kafka_decision_topic: str
    kafka_dlq_topic: str
    kafka_consumer_group: str
    kafka_client_id: str
    redis_url: str
    redis_active_set_key: str
    redis_executor_key_prefix: str
    redis_rules_key: str
    rules_local_ttl_seconds: float
    feature_extractor_mode: str
    feature_extractor_device: str | None
    model_root: str
    log_level: str

    @classmethod
    def from_env(cls) -> RuntimeSettings:
        return cls(
            kafka_bootstrap_servers=os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
            ),
            kafka_order_topic=os.getenv("KAFKA_ORDER_TOPIC", "ais.orders.v1"),
            kafka_decision_topic=os.getenv(
                "KAFKA_DECISION_RESULT_TOPIC", "decision.result.v1"
            ),
            kafka_dlq_topic=os.getenv(
                "KAFKA_DLQ_TOPIC", "decision-engine.dead-letter.v1"
            ),
            kafka_consumer_group=os.getenv(
                "KAFKA_CONSUMER_GROUP", "decision-engine-v1"
            ),
            kafka_client_id=os.getenv("KAFKA_CLIENT_ID", "decision-engine"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            redis_active_set_key=os.getenv(
                "REDIS_ACTIVE_SET_KEY", "executors:active"
            ),
            redis_executor_key_prefix=os.getenv(
                "REDIS_EXECUTOR_KEY_PREFIX", "executor:"
            ),
            redis_rules_key=os.getenv("REDIS_RULES_KEY", "rules:active"),
            rules_local_ttl_seconds=float(
                os.getenv("RULES_LOCAL_TTL_SECONDS", "5")
            ),
            feature_extractor_mode=os.getenv(
                "FEATURE_EXTRACTOR_MODE", "ml"
            ).lower(),
            feature_extractor_device=(
                os.getenv("FEATURE_EXTRACTOR_DEVICE") or None
            ),
            model_root=os.getenv(
                "MODEL_ROOT", str(Path.cwd() / "models")
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )

