import asyncio
import logging
import random
from typing import Optional
from ..storage.database import async_session_factory
from ..storage.repository import OrderRepository, ExecutorRepository
from ..kafka.producer import kafka_producer
from .load import load_generator

logger = logging.getLogger("ais.lifecycle")


class LifecycleSimulator:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.stats = {
            "accepted": 0,
            "rejected": 0,
            "awaiting": 0,
            "rework_created": 0,
            "executor_changes": 0,
        }

    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    async def start(self):
        if self.is_running():
            logger.warning("Lifecycle simulator is already running.")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Lifecycle simulator started.")

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Lifecycle simulator stopped.")

    async def _run_loop(self):
        tick = 0
        while self._running:
            try:
                await asyncio.sleep(random.uniform(2.5, 4.5))
                tick += 1

                # 1. Process orders lifecycle transitions
                async with async_session_factory() as session:
                    order_repo = OrderRepository(session)
                    candidates = await order_repo.get_random_orders(status="processed", limit=random.randint(3, 10))

                for order_row in candidates:
                    outcome = random.choices(["accept", "reject", "await"], weights=[55, 25, 20], k=1)[0]

                    async with async_session_factory() as session:
                        order_repo = OrderRepository(session)
                        updated_row, _, status_changed, prev_status, _ = await order_repo.update_order(
                            order_id=order_row.order_id,
                            new_status=outcome,
                        )

                    if updated_row and status_changed:
                        await kafka_producer.publish_order_status_changed(
                            order_id=updated_row.order_id,
                            previous_status=prev_status or "processed",
                            status=updated_row.status,
                            version=updated_row.version,
                        )

                        if outcome == "accept":
                            self.stats["accepted"] += 1
                        elif outcome == "reject":
                            self.stats["rejected"] += 1
                        elif outcome == "await":
                            self.stats["awaiting"] += 1

                            # Contract Section 7:
                            # "await -> новая заявка со статусом processed и заполненным parent_id"
                            child_order_dict = load_generator.generate_single_order_dict(
                                order_idx=random.randint(100000, 999999),
                                parent_id=updated_row.order_id,
                            )
                            async with async_session_factory() as session:
                                order_repo = OrderRepository(session)
                                child_row = await order_repo.create(
                                    order_id=child_order_dict["order_id"],
                                    parent_id=child_order_dict["parent_id"],
                                    status=child_order_dict["status"],
                                    weight=child_order_dict["weight"],
                                    attributes=child_order_dict["attributes"],
                                    version=1,
                                )
                            await kafka_producer.publish_order_created(child_row.to_dict())
                            self.stats["rework_created"] += 1

                # 2. Every 6 ticks (~20-25 seconds), simulate executor status/setting modifications
                if tick % 6 == 0:
                    async with async_session_factory() as session:
                        exec_repo = ExecutorRepository(session)
                        executors = await exec_repo.list_executors(limit=50)

                    if executors:
                        target = random.choice(executors)
                        action = random.choice(["toggle_active", "change_capacity"])

                        new_active = None
                        new_capacity = None
                        if action == "toggle_active":
                            new_active = not target.active
                        else:
                            new_capacity = round(random.choice([0.5, 1.0, 1.5, 2.0]), 1)

                        async with async_session_factory() as session:
                            exec_repo = ExecutorRepository(session)
                            updated_exec = await exec_repo.update_executor(
                                executor_id=target.executor_id,
                                active=new_active,
                                capacity=new_capacity,
                            )

                        if updated_exec:
                            await kafka_producer.publish_executor_updated(updated_exec.to_dict())
                            self.stats["executor_changes"] += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in lifecycle loop: {e}", exc_info=True)


lifecycle_simulator = LifecycleSimulator()
