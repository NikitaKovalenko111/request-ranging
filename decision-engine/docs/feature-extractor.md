# Feature Extractor

Feature Extractor is part of the common decision_engine package and runs after
Rule Engine. It receives the order text and only the executors that passed hard
constraints.

The runtime contract is exposed from decision_engine.feature_extractor.
HeuristicFeatureExtractor works without heavyweight ML dependencies.
PredictorFeatureExtractor adapts the existing transformer classifier and maps
its categorical complexity and urgency labels to normalized values for ML
Ranker.

The stage returns:

- normalized complexity and urgency;
- language and estimated effort;
- extracted keywords;
- per-executor skill match scores.

ML Ranker v1 consumes complexity and urgency. Skill match scores are retained in
PipelineResult and can become a trained Ranker feature in the next model version
without changing the pipeline boundary.

Classifier datasets are stored in data/feature_extractor/classifier. Local
matching samples are stored in examples/feature_extractor. Transformer tools
can be installed with the feature-extractor optional dependency group.
