import pandas as pd

from src.feature_builder import FEATURE_COLUMNS
from src.synthetic_generator import SyntheticDataGenerator, SyntheticGeneratorConfig
from src.train import split_by_order


def generator(seed: int = 7) -> SyntheticDataGenerator:
    return SyntheticDataGenerator(
        SyntheticGeneratorConfig(
            n_orders=24,
            candidates_per_order=5,
            executor_pool_size=20,
            seed=seed,
        )
    )


def test_generator_is_reproducible_and_has_grouped_candidates() -> None:
    first = generator().generate()
    second = generator().generate()

    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 24 * 5
    assert first.groupby("order_id", sort=False).size().eq(5).all()
    assert first.groupby("order_id")["executor_id"].nunique().eq(5).all()
    assert first["relevance"].between(0, 3).all()
    assert set(FEATURE_COLUMNS) <= set(first.columns)


def test_different_seed_changes_dataset() -> None:
    assert not generator(1).generate().equals(generator(2).generate())


def test_split_keeps_order_groups_isolated_and_temporal() -> None:
    frame = generator().generate()

    train, validation, test = split_by_order(
        frame, train_ratio=0.8, validation_ratio=0.1
    )
    train_ids = set(train["order_id"])
    validation_ids = set(validation["order_id"])
    test_ids = set(test["order_id"])

    assert train_ids.isdisjoint(validation_ids)
    assert train_ids.isdisjoint(test_ids)
    assert validation_ids.isdisjoint(test_ids)
    assert len(train) + len(validation) + len(test) == len(frame)
    assert train["order_timestamp"].max() < validation["order_timestamp"].min()
    assert validation["order_timestamp"].max() < test["order_timestamp"].min()

