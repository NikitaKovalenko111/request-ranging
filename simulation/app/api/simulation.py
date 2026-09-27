from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from ..storage.database import get_db_session
from ..storage.repository import OrderRepository, ExecutorRepository, AssignmentRepository
from ..generator.seeds import seed_database
from ..generator.load import load_generator
from ..generator.lifecycle import lifecycle_simulator
from ..kafka.producer import kafka_producer

router = APIRouter(prefix="/api/v1/simulation", tags=["Simulation Control"])


class StartSimulationRequest(BaseModel):
    mode: str = Field(default="linear_with_spikes", description="Modes: 'linear_with_spikes' (linear ~4000/h with spikes), 'stream_4k', 'wave', 'burst_at_start', 'normal', 'slow'")
    target_orders: int = Field(default=10000, description="Target total orders in database")
    orders_per_hour: Optional[float] = Field(default=4000.0, description="Target orders per hour")
    max_peak_per_sec: Optional[int] = Field(default=5, description="Max orders per second during spikes")
    start_lifecycle: bool = Field(default=True, description="Also start automatic lifecycle simulator")


class BurstRequest(BaseModel):
    count: int = Field(default=1000, ge=1, le=5000, description="Number of orders to generate instantly")


@router.post("/start")
async def start_simulation(
    req: StartSimulationRequest,
    session: AsyncSession = Depends(get_db_session),
):
    # Ensure database is seeded with preset executors
    await seed_database(session)

    await load_generator.start(
        mode=req.mode,
        target=req.target_orders,
        orders_per_hour=req.orders_per_hour,
        max_peak_per_sec=req.max_peak_per_sec,
    )
    if req.start_lifecycle and not lifecycle_simulator.is_running():
        await lifecycle_simulator.start()

    return {
        "status": "started",
        "mode": req.mode,
        "target_orders": req.target_orders,
        "orders_per_hour": load_generator.orders_per_hour,
        "max_peak_per_sec": load_generator.max_peak_per_sec,
        "lifecycle_running": lifecycle_simulator.is_running(),
    }


@router.post("/burst")
async def trigger_burst(
    req: BurstRequest,
):
    """
    Trigger instant burst of orders (e.g. 1000 orders in one moment).
    """
    res = await load_generator.execute_burst(count=req.count)
    return {
        "status": "burst_completed",
        "details": res,
    }


@router.post("/stop")
async def stop_simulation():
    await load_generator.stop()
    await lifecycle_simulator.stop()
    return {
        "status": "stopped",
        "generator_running": load_generator.is_running(),
        "lifecycle_running": lifecycle_simulator.is_running(),
    }


@router.post("/seed")
async def seed_data(session: AsyncSession = Depends(get_db_session)):
    await seed_database(session)
    return {"status": "seeded"}


@router.get("/status")
async def get_simulation_status(session: AsyncSession = Depends(get_db_session)):
    order_repo = OrderRepository(session)
    exec_repo = ExecutorRepository(session)
    assign_repo = AssignmentRepository(session)

    total_orders = await order_repo.count_orders()
    processed_orders = await order_repo.count_orders(status="processed")
    await_orders = await order_repo.count_orders(status="await")
    accept_orders = await order_repo.count_orders(status="accept")
    reject_orders = await order_repo.count_orders(status="reject")

    total_executors = await exec_repo.count_executors()
    active_executors = await exec_repo.count_executors(active=True)
    total_assignments = await assign_repo.count_assignments()

    return {
        "orders": {
            "total": total_orders,
            "processed": processed_orders,
            "await": await_orders,
            "accept": accept_orders,
            "reject": reject_orders,
        },
        "executors": {
            "total": total_executors,
            "active": active_executors,
            "inactive": total_executors - active_executors,
        },
        "assignments": {
            "total": total_assignments,
        },
        "load_generator": {
            "running": load_generator.is_running(),
            "mode": load_generator.mode,
            "current_rate_per_sec": load_generator.current_rate,
            "total_generated": load_generator.total_generated,
            "burst_count": load_generator.burst_count,
            "target_total": load_generator.target_total,
        },
        "lifecycle": {
            "running": lifecycle_simulator.is_running(),
            "stats": lifecycle_simulator.stats,
        },
        "kafka": {
            "connected": kafka_producer.is_connected,
            "in_memory_events_logged": len(kafka_producer.in_memory_log),
        },
    }
