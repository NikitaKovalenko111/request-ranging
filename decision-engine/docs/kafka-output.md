# Final Kafka output

DecisionPipeline publishes exactly one event after Rule Engine, Feature
Extractor, ML Ranker and Balancer have completed successfully.

Default topic:

```text
orders.decision-engine.completed
```

Environment variable:

```text
KAFKA_DECISION_RESULT_TOPIC=orders.decision-engine.completed
```

The Kafka message key is order_id encoded as UTF-8. This preserves per-order
partition ordering when the topic uses normal key-based partitioning.

Event shape:

```json
{
  "event_type": "ExecutorDecisionCompleted",
  "event_version": 1,
  "occurred_at": "2026-09-27T10:00:00+00:00",
  "order_id": "42",
  "balanced_candidates": [
    {
      "executor_id": "7",
      "rank": 1,
      "ml_score": 0.82,
      "effective_load": 0.2,
      "capacity": 1.0,
      "active_count": 1,
      "pending_count": 0,
      "processed_today": 5,
      "last_assignment_at": "2026-09-27T09:59:00+00:00"
    }
  ]
}
```

The selected executor is the first candidate, with rank equal to 1. An empty
balanced_candidates array means that no executor could be selected.

Intermediate Rule Engine, Feature Extractor and ML Ranker details remain
available in the in-process PipelineResult but are not sent to Kafka.

KafkaDecisionResultPublisher uses producer.send_and_wait. A delivery error is
propagated to the caller, so a Kafka consumer must commit its input offset only
after DecisionPipeline.decide returns successfully.

Use KafkaDecisionResultPublisher.from_env(producer) to read the topic from the
environment.
