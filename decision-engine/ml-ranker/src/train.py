from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path

from catboost import CatBoostRanker, Pool
import pandas as pd

from config import AppConfig, DEFAULT_CONFIG
from .evaluate import evaluate_model
from .feature_builder import FEATURE_COLUMNS
from .synthetic_generator import SyntheticDataGenerator, SyntheticGeneratorConfig


def split_by_order(
    frame: pd.DataFrame,
    *,
    train_ratio: float,
    validation_ratio: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    order_ids = frame["order_id"].drop_duplicates().tolist()
    count = len(order_ids)
    if count < 3:
        raise ValueError("at least three order groups are required")

    validation_count = max(1, int(count * validation_ratio))
    test_count = max(1, count - int(count * (train_ratio + validation_ratio)))
    train_count = count - validation_count - test_count
    if train_count < 1:
        raise ValueError("split ratios leave no training groups")

    train_ids = set(order_ids[:train_count])
    validation_ids = set(order_ids[train_count : train_count + validation_count])
    test_ids = set(order_ids[train_count + validation_count :])

    return (
        frame[frame["order_id"].isin(train_ids)].reset_index(drop=True),
        frame[frame["order_id"].isin(validation_ids)].reset_index(drop=True),
        frame[frame["order_id"].isin(test_ids)].reset_index(drop=True),
    )


def train_ranker(
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    config: AppConfig = DEFAULT_CONFIG,
) -> CatBoostRanker:
    train_pool = _pool(train_frame)
    validation_pool = _pool(validation_frame)
    model = CatBoostRanker(
        loss_function=config.model.loss_function,
        eval_metric=f"NDCG:top={config.model.ndcg_k}",
        iterations=config.model.iterations,
        depth=config.model.depth,
        learning_rate=config.model.learning_rate,
        random_seed=config.model.random_seed,
        verbose=config.model.verbose,
        allow_writing_files=False,
    )
    model.fit(
        train_pool,
        eval_set=validation_pool,
        use_best_model=True,
        early_stopping_rounds=50,
    )
    return model


def run_training(config: AppConfig = DEFAULT_CONFIG) -> dict[str, object]:
    generator = SyntheticDataGenerator(
        SyntheticGeneratorConfig(
            n_orders=config.data.n_orders,
            candidates_per_order=config.data.candidates_per_order,
            executor_pool_size=config.data.executor_pool_size,
            seed=config.data.seed,
        )
    )
    dataset = generator.generate()
    config.paths.processed_dataset.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(config.paths.processed_dataset, index=False)

    train_frame, validation_frame, test_frame = split_by_order(
        dataset,
        train_ratio=config.data.train_ratio,
        validation_ratio=config.data.validation_ratio,
    )
    model = train_ranker(train_frame, validation_frame, config)
    metrics = evaluate_model(model, test_frame, k=config.model.ndcg_k)

    config.paths.model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(config.paths.model_path))
    metadata = {
        "model_version": config.model.model_version,
        "created_at": datetime.now(UTC).isoformat(),
        "feature_columns": list(FEATURE_COLUMNS),
        "loss_function": config.model.loss_function,
        "dataset": {
            "rows": len(dataset),
            "orders": config.data.n_orders,
            "train_orders": int(train_frame["order_id"].nunique()),
            "validation_orders": int(validation_frame["order_id"].nunique()),
            "test_orders": int(test_frame["order_id"].nunique()),
            "synthetic": True,
            "seed": config.data.seed,
        },
        "metrics": {name: value.as_dict() for name, value in metrics.items()},
    }
    config.paths.metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata


def _pool(frame: pd.DataFrame) -> Pool:
    return Pool(
        data=frame.loc[:, FEATURE_COLUMNS],
        label=frame["relevance"],
        group_id=frame["order_id"],
        feature_names=list(FEATURE_COLUMNS),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the local CatBoost ranker")
    parser.add_argument("--orders", type=int, default=DEFAULT_CONFIG.data.n_orders)
    parser.add_argument(
        "--candidates",
        type=int,
        default=DEFAULT_CONFIG.data.candidates_per_order,
    )
    parser.add_argument(
        "--executors", type=int, default=DEFAULT_CONFIG.data.executor_pool_size
    )
    parser.add_argument(
        "--iterations", type=int, default=DEFAULT_CONFIG.model.iterations
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_CONFIG.paths.model_path)
    parser.add_argument(
        "--metadata", type=Path, default=DEFAULT_CONFIG.paths.metadata_path
    )
    arguments = parser.parse_args()

    config = replace(
        DEFAULT_CONFIG,
        data=replace(
            DEFAULT_CONFIG.data,
            n_orders=arguments.orders,
            candidates_per_order=arguments.candidates,
            executor_pool_size=arguments.executors,
        ),
        model=replace(DEFAULT_CONFIG.model, iterations=arguments.iterations),
        paths=replace(
            DEFAULT_CONFIG.paths,
            model_path=arguments.model,
            metadata_path=arguments.metadata,
        ),
    )
    metadata = run_training(config)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
