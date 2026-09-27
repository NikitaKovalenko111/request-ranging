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

Feature Extractor remains a separate project and is not part of this merge.

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
production can inject PredictorFeatureExtractor, MLRanker and RedisLoadRepository.
DecisionPipeline also requires a result publisher. Use
KafkaDecisionResultPublisher in production and InMemoryDecisionResultPublisher
in tests and local examples.
