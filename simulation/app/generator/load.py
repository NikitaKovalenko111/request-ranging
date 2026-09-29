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

# ==============================================================================
# НАСТРОЙКИ СКОРОСТИ И ПИКОВОЙ НАГРУЗКИ (МОЖНО МЕНЯТЬ ПРЯМО ЗДЕСЬ)
# ==============================================================================
TARGET_ORDERS_PER_HOUR: float = 4000.0   # Скорость потока: заявок в час (в среднем ~1.11 заявки/сек)
GENERATED_ORDER_WEIGHTS: tuple[float, ...] = (0.5, 1.0, 1.2, 1.5, 2.0)
MAX_PEAK_PER_SECOND: int = 5             # Максимальный пик: заявок в секунду во время скачка
SPIKE_PROBABILITY: float = 0.08          # Вероятность скачка (~8% времени - всплеск, 92% - ровный линейный поток)
MIN_SPIKE_ORDERS: int = 2                # Минимальный размер скачка при всплеске (от 2 до 5)
# ==============================================================================

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
        self.mode = "idle"  # idle, linear_with_spikes, stream_4k, wave, normal, slow
        self.total_generated = 0
        self.burst_count = 0
        self.current_rate = 0.0
        self.target_total = 10000

        # Настраиваемые параметры скорости
        self.orders_per_hour = TARGET_ORDERS_PER_HOUR
        self.max_peak_per_sec = MAX_PEAK_PER_SECOND
        self.spike_probability = SPIKE_PROBABILITY

    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def generate_single_order_dict(
        self,
        order_idx: int,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        order_id = f"order-{order_idx:05d}-{uuid.uuid4().hex[:6]}"
        is_vip = random.random() < 0.20
        # Keep every generated order assignable to at least one seeded
        # executor. Seeded capacity starts at 0.5 and reaches 2.0.
        weight = round(random.choice(GENERATED_ORDER_WEIGHTS), 2)
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
        Мгновенный залп на `count` заявок (например, 1000 заявок за долю секунды).
        """
        start_time = time.time()
        logger.info(f"Triggering INSTANT BURST of {count} orders...")

        async with async_session_factory() as session:
            repo = OrderRepository(session)
            await_ids = await repo.get_await_order_ids(limit=50)

        orders_to_insert = []
        base_index = self.total_generated + 1
        for i in range(count):
            order_idx = base_index + i
            parent_id = None
            if await_ids and random.random() < 0.12:
                parent_id = random.choice(await_ids)

            order_dict = self.generate_single_order_dict(order_idx, parent_id=parent_id)
            orders_to_insert.append(order_dict)

        chunk_size = 250
        for i in range(0, len(orders_to_insert), chunk_size):
            chunk = orders_to_insert[i : i + chunk_size]
            async with async_session_factory() as session:
                repo = OrderRepository(session)
                await repo.bulk_create(chunk, auto_commit=False)
                try:
                    for ord_dict in chunk:
                        await kafka_producer.publish_order_created(ord_dict)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

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

    async def start(
        self,
        mode: str = "linear_with_spikes",
        target: int = 10000,
        orders_per_hour: Optional[float] = None,
        max_peak_per_sec: Optional[int] = None,
    ):
        if self.is_running():
            logger.warning("Load generator is already running.")
            return

        if orders_per_hour is not None and orders_per_hour > 0:
            self.orders_per_hour = orders_per_hour
        if max_peak_per_sec is not None and max_peak_per_sec > 0:
            self.max_peak_per_sec = max_peak_per_sec

        self._running = True
        self.mode = mode
        self.target_total = target
        self._task = asyncio.create_task(self._run_loop(mode))
        logger.info(
            f"Started load generator in mode '{mode}': "
            f"base rate ~{self.orders_per_hour:.0f}/hour, max peak ~{self.max_peak_per_sec}/sec, target {target} orders."
        )

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
        Фоновый цикл генерации нагрузки:
          - 'linear_with_spikes' (по умолчанию): ровный линейный поток ~4000/час со случайными скачками до max_peak_per_sec.
          - 'stream_4k': чистый последовательный поток 4000/час (1 заявка каждые ~0.90 сек).
          - 'wave': волновой скачкообразный режим с крупными всплесками.
          - 'normal': 10 заявок/сек.
          - 'slow': 1 заявка/сек.
        """
        try:
            if mode == "burst_at_start":
                async with async_session_factory() as session:
                    repo = OrderRepository(session)
                    existing_count = await repo.count_orders()
                if existing_count < 1000:
                    await self.execute_burst(1000)

            while self._running:
                async with async_session_factory() as session:
                    repo = OrderRepository(session)
                    current_count = await repo.count_orders()
                    await_ids = await repo.get_await_order_ids(limit=50)

                if current_count >= self.target_total:
                    logger.info(f"Target of {self.target_total} orders reached ({current_count} in DB). Switching to maintenance rate.")
                    self.current_rate = 1.0
                    await asyncio.sleep(5.0)
                    continue

                # 1. Режим: в основном линейный поток ~4000/час со скачками до max_peak_per_sec
                if mode in ("linear_with_spikes", "default"):
                    is_spike = random.random() < self.spike_probability
                    if is_spike:
                        # Скачок: в эту секунду вылетает пачка заявок (до max_peak_per_sec)
                        step_orders = random.randint(MIN_SPIKE_ORDERS, max(MIN_SPIKE_ORDERS, self.max_peak_per_sec))
                        delay = 1.0
                    else:
                        # Линейный ровный шаг: по 1 заявке с интервалом под целевую часовую скорость
                        step_orders = 1
                        base_interval = 3600.0 / max(self.orders_per_hour, 1.0)  # ~0.90 сек при 4000/ч
                        delay = random.uniform(base_interval * 0.95, base_interval * 1.05)

                elif mode in ("stream_4k", "hourly_4000", "stream"):
                    # Строго последовательный поток ~4000 заявок/час (1 заявка каждые ~0.90с)
                    step_orders = 1
                    base_interval = 3600.0 / max(self.orders_per_hour, 1.0)
                    delay = random.uniform(base_interval * 0.98, base_interval * 1.02)

                elif mode in ("wave", "burst_at_start"):
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
                        step_orders = random.randint(25, max(25, self.max_peak_per_sec * 2))
                        delay = random.uniform(0.3, 0.6)
                    else:
                        step_orders = random.randint(50, 100)
                        delay = random.uniform(0.2, 0.5)

                elif mode == "normal":
                    step_orders = 5
                    delay = 0.5
                elif mode == "slow":
                    step_orders = 1
                    delay = 1.0
                else:
                    step_orders = 1
                    delay = 3600.0 / max(self.orders_per_hour, 1.0)

                # Генерация пачки заявок
                orders_batch = []
                base_idx = current_count + 1
                for i in range(step_orders):
                    parent_id = None
                    if await_ids and random.random() < 0.15:
                        parent_id = random.choice(await_ids)
                    orders_batch.append(self.generate_single_order_dict(base_idx + i, parent_id=parent_id))

                # Вставка в БД и отправка в Kafka атомарно
                async with async_session_factory() as session:
                    repo = OrderRepository(session)
                    await repo.bulk_create(orders_batch, auto_commit=False)
                    try:
                        for ord_item in orders_batch:
                            await kafka_producer.publish_order_created(ord_item)
                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Failed to publish orders batch to Kafka, rolling back DB: {e}")
                        raise

                self.total_generated += len(orders_batch)
                self.current_rate = round(len(orders_batch) / max(delay, 0.01), 1)

                await asyncio.sleep(delay)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in load generator loop: {e}", exc_info=True)
            self._running = False


load_generator = LoadGenerator()
