"""Real end-to-end run with classifier, KeyBERT, embeddings and CatBoost."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import importlib.metadata
import json
import platform
from pathlib import Path
from time import perf_counter
from typing import Any

import torch
from sentence_transformers import SentenceTransformer

from manual_pipeline_run import NAMES, SUBJECT, candidates
from decision_engine import DecisionPipeline, PipelineOrder
from decision_engine.balancer import Balancer, ExecutorLoad, InMemoryLoadRepository
from decision_engine.feature_extractor import MLFeatureExtractor
from decision_engine.feature_extractor.classifier.predict import DEFAULT_MODEL_DIR, RequestPredictor
from decision_engine.feature_extractor.ml_extractor import DEFAULT_EMBEDDING_MODEL_DIR
from decision_engine.ml_ranker.config import DEFAULT_CONFIG
from decision_engine.ml_ranker.inference import MLRanker
from decision_engine.publisher import KafkaDecisionResultPublisher
from decision_engine.rule_engine.domain import OrderStatus, OrderType
from decision_engine.rule_engine.engine import default_rule_engine

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_DIR / "reports"
JSON_REPORT = REPORT_DIR / "full-pipeline-report.json"
MARKDOWN_REPORT = REPORT_DIR / "full-pipeline-report.md"
ORDER_TEXT = (
    "\u0421\u0440\u043e\u0447\u043d\u043e \u043f\u0440\u043e\u0432\u0435\u0441\u0442\u0438 \u044d\u043a\u0441\u043f\u0435\u0440\u0442\u0438\u0437\u0443 \u0437\u0430\u044f\u0432\u043b\u0435\u043d\u0438\u044f \u043d\u0430 \u043a\u043e\u043c\u043f\u0435\u043d\u0441\u0430\u0446\u0438\u044e "
    "\u043f\u043e\u0441\u043b\u0435 \u0437\u0430\u0442\u043e\u043f\u043b\u0435\u043d\u0438\u044f \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0433\u043e \u043f\u043e\u043c\u0435\u0449\u0435\u043d\u0438\u044f. \u041d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e \u043e\u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c "
    "\u043f\u043e\u0432\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f, \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0441\u0442\u0440\u0430\u0445\u043e\u0432\u043e\u0439 \u043f\u043e\u043b\u0438\u0441, \u0430\u043a\u0442\u044b \u0430\u0432\u0430\u0440\u0438\u0439\u043d\u043e\u0439 \u0441\u043b\u0443\u0436\u0431\u044b "
    "\u0438 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b \u043d\u0430 \u043e\u0431\u043e\u0440\u0443\u0434\u043e\u0432\u0430\u043d\u0438\u0435. \u0422\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f \u0440\u0430\u0441\u0441\u0447\u0438\u0442\u0430\u0442\u044c \u0440\u0430\u0437\u043c\u0435\u0440 \u0432\u044b\u043f\u043b\u0430\u0442\u044b, "
    "\u043f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u0438\u0442\u044c \u0441\u043c\u0435\u0442\u0443 \u0432\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0445 \u0440\u0430\u0431\u043e\u0442, \u043e\u0446\u0435\u043d\u0438\u0442\u044c \u044e\u0440\u0438\u0434\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u0440\u0438\u0441\u043a\u0438 "
    "\u043e\u0442\u043a\u0430\u0437\u0430 \u0438 \u0441\u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c \u0438\u0442\u043e\u0433\u043e\u0432\u043e\u0435 \u0437\u0430\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435. \u0420\u0435\u0448\u0435\u043d\u0438\u0435 \u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e \u043f\u0440\u0438\u043d\u044f\u0442\u044c \u043d\u0435 \u043f\u043e\u0437\u0434\u043d\u0435\u0435 "
    "\u0437\u0430\u0432\u0442\u0440\u0430\u0448\u043d\u0435\u0433\u043e \u0434\u043d\u044f, \u043f\u043e\u0441\u043a\u043e\u043b\u044c\u043a\u0443 \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u0430 \u0443\u0432\u0435\u043b\u0438\u0447\u0438\u0432\u0430\u0435\u0442 \u0443\u0431\u044b\u0442\u043a\u0438."
)

class Timings:
    def __init__(self) -> None:
        self.values: dict[str, float] = {}
    def call(self, name: str, function: Any, *args: Any, **kwargs: Any) -> Any:
        started = perf_counter()
        result = function(*args, **kwargs)
        self.values[name] = perf_counter() - started
        return result
    async def async_call(self, name: str, function: Any, *args: Any, **kwargs: Any) -> Any:
        started = perf_counter()
        result = await function(*args, **kwargs)
        self.values[name] = perf_counter() - started
        return result

class TimedRuleEngine:
    def __init__(self, delegate: Any, timings: Timings) -> None:
        self.delegate, self.timings = delegate, timings
    def filter(self, *args: Any, **kwargs: Any) -> Any:
        return self.timings.call("rule_engine", self.delegate.filter, *args, **kwargs)

class TimedFeatureExtractor:
    def __init__(self, delegate: Any, timings: Timings) -> None:
        self.delegate, self.timings = delegate, timings
    def extract(self, *args: Any, **kwargs: Any) -> Any:
        return self.timings.call("feature_extractor", self.delegate.extract, *args, **kwargs)

class TimedRanker:
    def __init__(self, delegate: Any, timings: Timings) -> None:
        self.delegate, self.timings = delegate, timings
        self.model_version = delegate.model_version
    def rank(self, *args: Any, **kwargs: Any) -> Any:
        return self.timings.call("ml_ranker", self.delegate.rank, *args, **kwargs)

class TimedBalancer:
    def __init__(self, delegate: Any, timings: Timings) -> None:
        self.delegate, self.timings = delegate, timings
    async def balance(self, *args: Any, **kwargs: Any) -> Any:
        return await self.timings.async_call("balancer", self.delegate.balance, *args, **kwargs)

class RecordingKafkaProducer:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
    async def send_and_wait(self, topic: str, value: bytes, key: bytes | None = None) -> None:
        self.messages.append({"topic": topic, "key": key.decode() if key else None, "payload": json.loads(value), "payload_bytes": len(value)})

class TimedPublisher:
    def __init__(self, delegate: Any, timings: Timings) -> None:
        self.delegate, self.timings = delegate, timings
    async def publish(self, *args: Any, **kwargs: Any) -> Any:
        return await self.timings.async_call("kafka_serialization_and_publish", self.delegate.publish, *args, **kwargs)

def role(executor_id: str) -> str:
    return NAMES[executor_id]

def build_loads(now: datetime) -> dict[str, ExecutorLoad]:
    return {
        "101": ExecutorLoad(4, 4.0, 1, 0.8, 12, now - timedelta(minutes=4)),
        "102": ExecutorLoad(1, 1.0, 0, 0.0, 7, now - timedelta(minutes=25)),
        "103": ExecutorLoad(1, 0.5, 0, 0.0, 9, now - timedelta(minutes=12)),
        "104": ExecutorLoad(0, 0.0, 1, 0.4, 3, now - timedelta(hours=2)),
    }

def profile_input(profiles: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "executor_id": str(item.user_id),
            "role": role(str(item.user_id)),
            "experience_score": item.experience_score,
            "speed_score": item.speed_score,
            "reliability_score": item.reliability_score,
            "historical_success_rate": item.historical_success_rate,
            "historical_avg_processing_time": item.historical_avg_processing_time,
            "historical_orders_count": item.historical_orders_count,
            "capacity": item.capacity,
            "active": item.active,
            "daily_count": item.daily_count,
            "max_daily_limit": item.settings.max_daily_limit,
            "skills": list(item.skills),
        }
        for item in profiles
    ]

def load_input(loads: dict[str, ExecutorLoad]) -> dict[str, dict[str, Any]]:
    return {
        executor_id: {
            "active_count": item.active_count,
            "active_weight": item.active_weight,
            "pending_count": item.pending_count,
            "pending_weight": item.pending_weight,
            "processed_today": item.processed_today,
            "last_assignment_at": item.last_assignment_at.isoformat() if item.last_assignment_at else None,
        }
        for executor_id, item in loads.items()
    }

async def run() -> dict[str, Any]:
    now = datetime.now(UTC)
    total_started = perf_counter()
    initialization, stages = Timings(), Timings()
    predictor = initialization.call(
        "classifier_load", RequestPredictor, DEFAULT_MODEL_DIR, torch.device("cpu")
    )
    embedding = initialization.call(
        "embedding_model_load", SentenceTransformer, str(DEFAULT_EMBEDDING_MODEL_DIR),
        local_files_only=True, device="cpu",
    )
    extractor = initialization.call(
        "keybert_initialization", MLFeatureExtractor, predictor, embedding, max_keywords=15
    )
    ranker = initialization.call(
        "catboost_ranker_load", MLRanker,
        DEFAULT_CONFIG.paths.model_path, DEFAULT_CONFIG.paths.metadata_path,
    )
    executor_profiles = candidates()
    loads = build_loads(now)
    producer = RecordingKafkaProducer()
    pipeline = DecisionPipeline(
        TimedRuleEngine(default_rule_engine(), stages),
        TimedFeatureExtractor(extractor, stages),
        TimedRanker(ranker, stages),
        TimedBalancer(Balancer(InMemoryLoadRepository(loads)), stages),
        TimedPublisher(KafkaDecisionResultPublisher(
            producer, topic="orders.decision-engine.completed"
        ), stages),
    )
    order = PipelineOrder(
        id="CLAIM-2026-00042", timestamp=now, sum=185_000,
        order_type=OrderType.ORDER_2, subject=SUBJECT,
        status=OrderStatus.PROCESSED, weight=0.8, text=ORDER_TEXT,
    )
    pipeline_started = perf_counter()
    result = await pipeline.decide(order, executor_profiles)
    pipeline_total = perf_counter() - pipeline_started
    report = {
        "run": {
            "started_at": now.isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "device": "cpu",
            "library_versions": {
                name: importlib.metadata.version(name)
                for name in ("torch", "transformers", "sentence-transformers", "keybert", "catboost")
            },
        },
        "models": {
            "classifier": str(DEFAULT_MODEL_DIR),
            "embedding": str(DEFAULT_EMBEDDING_MODEL_DIR),
            "ranker": str(DEFAULT_CONFIG.paths.model_path),
            "ranker_version": ranker.model_version,
        },
        "input": {
            "order": {
                "id": order.id, "timestamp": order.timestamp.isoformat(),
                "sum": order.sum, "order_type": order.order_type.value,
                "subject": str(order.subject), "status": order.status.value,
                "weight": order.weight, "text": order.text,
            },
            "candidates": profile_input(executor_profiles),
            "runtime_loads": load_input(loads),
        },
        "output": {
            "rule_engine": {
                "eligible": [
                    {"executor_id": str(item), "role": role(str(item))}
                    for item in result.rule_result.eligible_executor_ids
                ],
                "rejected": [
                    {
                        "executor_id": str(item.executor_id),
                        "role": role(str(item.executor_id)),
                        "violations": [violation.as_dict() for violation in item.violations],
                    }
                    for item in result.rule_result.rejected
                ],
            },
            "feature_extractor": {
                "features": result.extracted_features.as_dict(),
                "diagnostics": extractor.last_diagnostics,
            },
            "ml_ranking": [
                {**item.as_dict(), "role": role(item.executor_id)}
                for item in result.ml_ranking
            ],
            "balanced_candidates": [
                {**item.as_dict(), "role": role(item.executor_id)}
                for item in result.balanced_candidates
            ],
            "selected_executor": {
                "executor_id": result.selected_executor_id,
                "role": role(result.selected_executor_id) if result.selected_executor_id else None,
            },
            "kafka": producer.messages[0],
        },
        "timings_seconds": {
            "initialization": initialization.values,
            "pipeline_stages": stages.values,
            "pipeline_total": pipeline_total,
            "cold_start_end_to_end_total": perf_counter() - total_started,
        },
    }
    return report

def markdown(report: dict[str, Any]) -> str:
    order, output = report["input"]["order"], report["output"]
    timings = report["timings_seconds"]
    features = output["feature_extractor"]["features"]
    labels = output["feature_extractor"]["diagnostics"]["classifier_labels"]
    lines = [
        "# Full Decision Engine run", "",
        f"- Order: `{order['id']}`",
        f"- Ranker: `{report['models']['ranker_version']}`",
        f"- Pipeline: `{timings['pipeline_total']:.3f} s`",
        f"- Cold start total: `{timings['cold_start_end_to_end_total']:.3f} s`",
        "", "## Original order text", "", order["text"], "",
        "## Candidates", "",
        "| ID | Role | Exp | Speed | Reliability | Capacity | Active | Daily |",
        "|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for item in report["input"]["candidates"]:
        lines.append(
            f"| {item['executor_id']} | {item['role']} | {item['experience_score']:.2f} | "
            f"{item['speed_score']:.2f} | {item['reliability_score']:.2f} | "
            f"{item['capacity']:.2f} | {item['active']} | "
            f"{item['daily_count']}/{item['max_daily_limit']} |"
        )
    lines += [
        "", "## Rule Engine", "",
        f"- Eligible: {', '.join(i['executor_id'] for i in output['rule_engine']['eligible'])}",
        f"- Rejected: `{json.dumps(output['rule_engine']['rejected'], ensure_ascii=False)}`",
        "", "## Feature Extractor", "",
        f"- Classifier labels: `{json.dumps(labels, ensure_ascii=False)}`",
        f"- Complexity: `{features['complexity']}`",
        f"- Urgency: `{features['urgency']}`",
        f"- KeyBERT keywords: {', '.join(features['keywords'])}",
        f"- Embedding scores: `{json.dumps(features['skill_match_scores'], ensure_ascii=False)}`",
        "", "## ML ranking", "",
        "| Rank | ID | Role | Score |", "|---:|---|---|---:|",
    ]
    for item in output["ml_ranking"]:
        lines.append(f"| {item['rank']} | {item['executor_id']} | {item['role']} | {item['score']:.6f} |")
    lines += ["", "## Balancer", "",
              "| Rank | ID | Role | ML score | Effective load |",
              "|---:|---|---|---:|---:|"]
    for item in output["balanced_candidates"]:
        lines.append(
            f"| {item['rank']} | {item['executor_id']} | {item['role']} | "
            f"{item['ml_score']:.6f} | {item['effective_load']:.6f} |"
        )
    selected = output["selected_executor"]
    lines += ["", f"Selected: **{selected['role']} ({selected['executor_id']})**",
              "", "## Initialization timings", ""]
    lines += [f"- {name}: `{value:.3f} s`" for name, value in timings["initialization"].items()]
    lines += ["", "## Pipeline timings", ""]
    lines += [f"- {name}: `{value:.3f} s`" for name, value in timings["pipeline_stages"].items()]
    lines += [
        "", "## Kafka output", "",
        f"- Topic: `{output['kafka']['topic']}`",
        f"- Key: `{output['kafka']['key']}`",
        f"- Payload: `{output['kafka']['payload_bytes']} bytes`", "",
        "Full KeyBERT weights, embedding similarities, runtime loads, candidate data "
        "and Kafka payload are included in the JSON report.", "",
    ]
    return "\n".join(lines)

async def main() -> None:
    report = await run()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    MARKDOWN_REPORT.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({
        "selected_executor": report["output"]["selected_executor"],
        "pipeline_seconds": report["timings_seconds"]["pipeline_total"],
        "cold_start_seconds": report["timings_seconds"]["cold_start_end_to_end_total"],
        "json_report": str(JSON_REPORT),
        "markdown_report": str(MARKDOWN_REPORT),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
