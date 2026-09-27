from .orders import router as orders_router
from .executors import router as executors_router
from .assignments import router as assignments_router
from .simulation import router as simulation_router

__all__ = [
    "orders_router",
    "executors_router",
    "assignments_router",
    "simulation_router",
]
