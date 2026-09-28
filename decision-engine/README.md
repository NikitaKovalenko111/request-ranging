# Executor Decision Engine

Полная инструкция по установке: [docs/setup.md](docs/setup.md).

One Python project for the complete executor selection pipeline:

1. Rule Engine rejects candidates that violate mandatory rules.
2. Feature Extractor enriches the order and eligible candidates.
3. ML Ranker scores the enriched eligible candidates.
4. Balancer uses runtime load and returns the final order.
5. Kafka publisher sends the completed decision event.

All modules share one namespace:

- decision_engine.rule_engine
- decision_engine.feature_extractor
- decision_engine.ml_ranker
- decision_engine.balancer
- decision_engine.pipeline
- decision_engine.publisher

The production command decision-engine-worker consumes AIS order events,
loads backend-owned profiles and runtime load from Redis, runs the complete
pipeline and publishes ExecutorDecisionCompleted to decision.result.v1. By
default it uses the local classifier, KeyBERT and embedding skill matching.
Set FEATURE_EXTRACTOR_MODE=heuristic only for a lightweight local fallback.

## Install and test

```powershell
cd decision-engine
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e '.[dev]'
.venv\Scripts\python -m pytest
```

Transformer-based Feature Extractor tools are optional:

```powershell
.venv\Scripts\python -m pip install -e '.[dev,feature-extractor]'
```

## Commands

```powershell
.venv\Scripts\decision-rule-worker
.venv\Scripts\decision-ranker-train
.venv\Scripts\decision-ranker-demo
.venv\Scripts\decision-feature-predict
```

ML artifacts live in models, datasets in data, and rule examples in examples.
Module-specific documentation is retained in docs.

DecisionPipeline accepts a PipelineOrder and ExecutorProfile list. Rule Engine
runs first; Feature Extractor receives only eligible executors. Its async
decide method returns all stage results and selected_executor_id. Local runs can
use HeuristicFeatureExtractor, HeuristicRanker and InMemoryLoadRepository;
production uses MLFeatureExtractor, MLRanker and RedisHashLoadRepository.
DecisionPipeline also requires a result publisher. Use
KafkaDecisionResultPublisher in production and InMemoryDecisionResultPublisher
in tests and local examples.
