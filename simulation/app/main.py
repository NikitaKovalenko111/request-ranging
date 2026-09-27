import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .storage.database import init_db, async_session_factory
from .kafka.producer import kafka_producer, KafkaPublishError
from .generator.seeds import seed_database
from .generator.load import load_generator
from .generator.lifecycle import lifecycle_simulator
from .api.orders import router as orders_router
from .api.executors import router as executors_router
from .api.assignments import router as assignments_router
from .api.simulation import router as simulation_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ais.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AIS Simulator...")
    # 1. Initialize DB tables
    await init_db()
    logger.info("Database initialized.")

    # 2. Start Kafka producer
    await kafka_producer.start()

    # 3. Seed preset executors (do not pre-seed orders silently: orders stream through Kafka)
    async with async_session_factory() as session:
        await seed_database(session, seed_orders=False)

    logger.info("AIS Simulator startup completed.")
    yield

    # Shutdown
    logger.info("Shutting down AIS Simulator...")
    await load_generator.stop()
    await lifecycle_simulator.stop()
    await kafka_producer.stop()
    logger.info("AIS Simulator shutdown completed.")


app = FastAPI(
    title="AIS Simulator",
    description="External AIS Mock for Executor Balancer Hackathon",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(KafkaPublishError)
async def kafka_publish_error_handler(request: Request, exc: KafkaPublishError):
    return JSONResponse(
        status_code=500,
        content={"code": "KAFKA_PUBLISH_FAILED", "message": str(exc), "retryable": True},
    )


# Enable CORS for frontend dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(orders_router)
app.include_router(executors_router)
app.include_router(assignments_router)
app.include_router(simulation_router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "AIS Simulator",
        "status": "online",
        "contract_version": 1,
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
