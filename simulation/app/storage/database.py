import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from ..config import settings

Base = declarative_base()

# Configure engine
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# SQLite optimization hooks
if "sqlite" in settings.database_url:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=10000;")
        cursor.execute("PRAGMA cache_size=-64000;")
        cursor.close()

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # SQLite migrations for existing databases
        if "sqlite" in settings.database_url:
            def migrate_sqlite(sync_conn):
                # 1. Add skills_json column to executors if not present
                res = sync_conn.exec_driver_sql("PRAGMA table_info(executors);")
                columns = [row[1] for row in res.fetchall()]
                if columns and "skills_json" not in columns:
                    sync_conn.exec_driver_sql("ALTER TABLE executors ADD COLUMN skills_json TEXT NOT NULL DEFAULT '[]';")

                # 2. Ensure unique index on assignments(order_id)
                sync_conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_assignments_order_id ON assignments(order_id);")

            await conn.run_sync(migrate_sqlite)
