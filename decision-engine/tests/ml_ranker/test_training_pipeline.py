from datetime import UTC, datetime

from decision_engine.ml_ranker.config import AppConfig, DataConfig, ModelConfig, PathConfig
from decision_engine.ml_ranker.feature_builder import FEATURE_COLUMNS
from decision_engine.ml_ranker.inference import MLRanker
from decision_engine.ml_ranker.schemas import Executor, Order
from decision_engine.ml_ranker.train import run_training


def test_training_saves_loadable_model_and_metadata(tmp_path) -> None:
    config = AppConfig(
        data=DataConfig(
            n_orders=80,
            candidates_per_order=5,
            executor_pool_size=30,
            seed=11,
            train_ratio=0.7,
            validation_ratio=0.15,
        ),
        model=ModelConfig(iterations=8, depth=4, verbose=0, random_seed=11),
        paths=PathConfig(
            processed_dataset=tmp_path / "dataset.csv",
            model_path=tmp_path / "ranker.cbm",
            metadata_path=tmp_path / "metadata.json",
        ),
    )

    metadata = run_training(config)

    assert config.paths.processed_dataset.exists()
    assert config.paths.model_path.exists()
    assert config.paths.metadata_path.exists()
    assert tuple(metadata["feature_columns"]) == FEATURE_COLUMNS
    assert set(metadata["metrics"]) == {"heuristic", "ml"}

    ranker = MLRanker(config.paths.model_path, config.paths.metadata_path)
    order = Order("O", datetime.now(UTC), complexity=0.7, urgency=0.8)
    candidates = [
        Executor("E1", 0.8, 0.9, 0.9, 0.9, 8.0, 300),
        Executor("E2", 0.5, 0.5, 0.7, 0.7, 20.0, 50),
    ]

    ranking = ranker.rank(order, candidates)

    assert len(ranking) == 2
    assert ranking[0].score >= ranking[1].score
    assert all(0.0 <= item.score <= 1.0 for item in ranking)
