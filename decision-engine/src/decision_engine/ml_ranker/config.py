from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class DataConfig:
    n_orders: int = 5_000
    candidates_per_order: int = 10
    executor_pool_size: int = 500
    seed: int = 42
    train_ratio: float = 0.8
    validation_ratio: float = 0.1

    def __post_init__(self) -> None:
        if self.n_orders < 3:
            raise ValueError("n_orders must be at least 3")
        if self.candidates_per_order < 2:
            raise ValueError("candidates_per_order must be at least 2")
        if self.executor_pool_size < self.candidates_per_order:
            raise ValueError("executor_pool_size must cover candidates_per_order")
        if not 0 < self.train_ratio < 1:
            raise ValueError("train_ratio must be between 0 and 1")
        if not 0 < self.validation_ratio < 1:
            raise ValueError("validation_ratio must be between 0 and 1")
        if self.train_ratio + self.validation_ratio >= 1:
            raise ValueError("train and validation ratios must leave a test split")


@dataclass(frozen=True, slots=True)
class ModelConfig:
    model_version: str = "ranker-v1"
    loss_function: str = "YetiRankPairwise"
    iterations: int = 350
    depth: int = 7
    learning_rate: float = 0.08
    random_seed: int = 42
    ndcg_k: int = 5
    verbose: int = 50


@dataclass(frozen=True, slots=True)
class PathConfig:
    processed_dataset: Path = PROJECT_DIR / "data" / "processed" / "ranking_dataset.csv"
    model_path: Path = PROJECT_DIR / "models" / "ranker-v1.cbm"
    metadata_path: Path = PROJECT_DIR / "models" / "ranker-v1.metadata.json"


@dataclass(frozen=True, slots=True)
class AppConfig:
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    paths: PathConfig = field(default_factory=PathConfig)


DEFAULT_CONFIG = AppConfig()

