import asyncio
import logging
import random
import time
import uuid
from typing import Any, Dict, List, Optional
from ..storage.database import async_session_factory
from ..storage.repository import OrderRepository
from ..kafka.producer import kafka_producer

logger = logging.getLogger("ais.load_generator")

ORDER_TYPES = ["LEGAL_REVIEW", "CONSULTATION", "CLAIM_PROCESSING"]
SUBJECTS = ["contract", "claims", "payments", "compliance"]
CLIENT_MSPS = ["small", "medium", "large"]
EXECUTOR_MSPS = ["legal", "consulting", "claims_dept"]
REGIONS = ["ural", "siberia", "central", "volga", "south"]
TEXT_TEMPLATES = [
    "Проверка договора поставки оборудования",
    "Консультация по налоговым рискам контракта",
    "Претензия по задержке оплаты счета",
    "Проверка соблюдения комплаенс процедур",
    "Анализ соглашения о конфиденциальности",
    "Срочная экспертиза досудебной претензии",
]


class LoadGenerator:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.mode = "idle"  # idle, wave, normal, slow, target_10k
        self.total_generated = 0
        self.burst_count = 0
        self.current_rate = 0.0
        self.target_total = 10000

    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def generate_single_order_dict(
        self,
        order_idx: int,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        order_id = f"order-{order_idx:05d}-{uuid.uuid4().hex[:6]}"
        is_vip = random.random() < 0.20
        weight = round(random.choice([0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]), 2)
        sum_value = random.choice([
            random.randint(50_000, 300_000),
            random.randint(300_000, 1_000_000),
            random.randint(1_000_000, 5_000_000),
        ])

        return {
            "order_id": order_id,
            "parent_id": parent_id,
            "status": "processed",
            "weight": weight,
            "version": 1,
            "attributes": {
                "sum": sum_value,
                "order_type": random.choice(ORDER_TYPES),
                "subject": random.choice(SUBJECTS),
                "vip": is_vip,
                "client_msp": random.choice(CLIENT_MSPS),
                "executor_msp": random.choice(EXECUTOR_MSPS),
                "text": random.choice(TEXT_TEMPLATES),
                "region": random.choice(REGIONS),
            },
        }

    async def execute_burst(self, count: int = 1000) -> Dict[str, Any]:
        """
        Instant burst of `count` orders (e.g. 1000 orders in one moment).
        Uses chunked bulk inserts and batch event publishing for maximum speed.
        """
        start_time = time.time()
        logger.info(f"Triggering INSTANT BURST of {count} orders...")

        async with async_session_factory() as session:
            repo = OrderRepository(session)
            await_ids = await repo.get_await_order_ids(limit=50)

        orders_to_insert = []
        batch_events = []

        base_index = self.total_generated + 1
        for i in range(count):
            order_idx = base_index + i
            parent_id = None
            if await_ids and random.random() < 0.12:
                parent_id = random.choice(await_ids)

            order_dict = self.generate_single_order_dict(order_idx, parent_id=parent_id)
            orders_to_insert.append(order_dict)

        # Batch insert in chunks of 250 for database stability
        chunk_size = 250
        for i in range(0, len(orders_to_insert), chunk_size):
            chunk = orders_to_insert[i : i + chunk_size]
            async with async_session_factory() as session:
                repo = OrderRepository(session)
                await repo.bulk_create(chunk)

            # Publish order created events
            for ord_dict in chunk:
                await kafka_producer.publish_order_created(ord_dict)

        elapsed = time.time() - start_time
        self.total_generated += count
        self.burst_count += 1
        rate = count / max(elapsed, 0.001)

        logger.info(f"Burst of {count} orders completed in {elapsed:.2f}s ({rate:.0f} orders/sec).")
        return {
            "burst_orders": count,
            "elapsed_seconds": round(elapsed, 2),
            "effective_rate": round(rate, 1),
            "total_generated": self.total_generated,
        }

    async def start(self, mode: str = "wave", target: int = 10000):
        if self.is_running():
            logger.warning("Load generator is already running.")
            return

        self._running = True
        self.mode = mode
        self.target_total = target
        self._task = asyncio.create_task(self._run_loop(mode))
        logger.info(f"Started load generator in mode '{mode}' with target {target} orders.")

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.current_rate = 0.0
        self.mode = "idle"
        logger.info("Load generator stopped.")

    async def _run_loop(self, mode: str):
        """
        Background loop generating fluctuating / jumping load up to target_total.
        Modes:
          - 'wave': rate jumps erratically (e.g. 2 req/s -> 30 req/s -> 80 req/s -> 5 req/s)
          - 'burst_at_start': immediately fires 1k burst, then wave fluctuations
          - 'normal': steady ~10 orders/sec
          - 'slow': steady ~1 order/sec
        """
        try:
            # Check if burst at start is requested
            if mode in ("burst_at_start", "wave"):
                # Initial 1k burst if total orders are low (< 1000)
                async with async_session_factory() as session:
                    repo = OrderRepository(session)
                    existing_count = await repo.count_orders()
                if existing_count < 1000 and mode == "burst_at_start":
                    await self.execute_burst(1000)

            while self._running:
                # Check target limit
                async with async_session_factory() as session:
                    repo = OrderRepository(session)
                    current_count = await repo.count_orders()
                    await_ids = await repo.get_await_order_ids(limit=50)

                if current_count >= self.target_total:
                    logger.info(f"Target of {self.target_total} orders reached ({current_count} in DB). Switching to maintenance rate.")
                    self.current_rate = 1.0
                    await asyncio.sleep(5.0)
                    continue

                # Determine fluctuating rate ("а так они прыгали")
                if mode in ("wave", "burst_at_start"):
                    # Fluctuating state machine:
                    state = random.choices(
                        ["calm", "moderate", "spike", "micro_burst"],
                        weights=[40, 35, 15, 10],
                        k=1,
                    )[0]

                    if state == "calm":
                        step_orders = random.randint(1, 4)
                        delay = random.uniform(0.5, 1.2)
                    elif state == "moderate":
                        step_orders = random.randint(8, 20)
                        delay = random.uniform(0.4, 0.8)
                    elif state == "spike":
                        step_orders = random.randint(30, 60)
                        delay = random.uniform(0.3, 0.6)
                    else:  # micro_burst
                        step_orders = random.randint(80, 150)
                        delay = random.uniform(0.2, 0.5)

                elif mode == "normal":
                    step_orders = 5
                    delay = 0.5
                elif mode == "slow":
                    step_orders = 1
                    delay = 1.0
                else:
                    step_orders = 5
                    delay = 0.5

                # Generate step orders
                orders_batch = []
                base_idx = current_count + 1
                for i in range(step_orders):
                    parent_id = None
                    if await_ids and random.random() < 0.15:
                        parent_id = random.choice(await_ids)
                    orders_batch.append(self.generate_single_order_dict(base_idx + i, parent_id=parent_id))

                # Insert and publish
                async with async_session_factory() as session:
                    repo = OrderRepository(session)
                    await repo.bulk_create(orders_batch)

                for ord_item in orders_batch:
                    await kafka_producer.publish_order_created(ord_item)

                self.total_generated += len(orders_batch)
                self.current_rate = round(len(orders_batch) / max(delay, 0.01), 1)

                await asyncio.sleep(delay)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in load generator loop: {e}", exc_info=True)
            self._running = False


load_generator = LoadGenerator()
