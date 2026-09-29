from statistics import mean

from simulation.app.generator.load import (
    GENERATED_ORDER_WEIGHTS,
    TARGET_ORDERS_PER_HOUR,
    LoadGenerator,
)
from simulation.app.generator.populate_10k import generate_10k_orders_data
from simulation.app.generator.seeds import PRESET_EXECUTORS


def test_seed_pool_is_sized_for_4k_per_hour() -> None:
    active = [executor for executor in PRESET_EXECUTORS if executor["active"]]
    active_capacity = sum(float(executor["capacity"]) for executor in active)

    assert len(PRESET_EXECUTORS) == 40
    assert len(active) == 38
    assert active_capacity == 62.0

    # Little's law sizing for the current simulator:
    # 4000 orders/hour, a conservative 30-second end-to-end residence time,
    # average generated weight, and no more than 70% planned utilization.
    required_capacity = (
        TARGET_ORDERS_PER_HOUR
        * (30.0 / 3600.0)
        * mean(GENERATED_ORDER_WEIGHTS)
        / 0.70
    )
    assert active_capacity >= required_capacity


def test_stream_generator_never_exceeds_seeded_order_capacity() -> None:
    generator = LoadGenerator()

    generated = [
        generator.generate_single_order_dict(order_idx=index)
        for index in range(1, 2001)
    ]

    assert max(order["weight"] for order in generated) <= 2.0


def test_bulk_generator_never_exceeds_seeded_order_capacity() -> None:
    generated = generate_10k_orders_data()

    assert len(generated) == 10_000
    assert max(order["weight"] for order in generated) <= 2.0
