import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["KAFKA_ENABLED"] = "false"
os.environ["ASSIGNMENT_DELAY_MIN"] = "0s"
os.environ["ASSIGNMENT_DELAY_MAX"] = "0s"

from simulation.app.config import settings
settings.assignment_delay_min = 0.0
settings.assignment_delay_max = 0.0
settings.kafka_enabled = False

from simulation.app.main import app
from simulation.app.storage.database import engine, Base, async_session_factory
from simulation.app.generator.seeds import seed_database


@pytest_asyncio.fixture(scope="function")
async def client():
    # Setup test DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed executors
    async with async_session_factory() as session:
        await seed_database(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
