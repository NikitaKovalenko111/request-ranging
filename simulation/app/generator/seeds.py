import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..storage.repository import ExecutorRepository, OrderRepository
from ..kafka.producer import kafka_producer

logger = logging.getLogger("ais.seeds")

PRESET_EXECUTORS: List[Dict[str, Any]] = [
    {
        "executor_id": "executor-01",
        "active": True,
        "capacity": 1.0,
        "daily_limit": 50,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 500000,
            "client_msp": ["small", "medium"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW"],
            "subjects": ["contract"],
            "vip_allowed": False,
            "regions": ["ural", "central"],
        },
    },
    {
        "executor_id": "executor-02",
        "active": True,
        "capacity": 1.0,
        "daily_limit": 60,
        "attributes": {
            "min_accept_sum": 50000,
            "max_accept_sum": 800000,
            "client_msp": ["medium", "large"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW", "CONSULTATION"],
            "subjects": ["contract", "compliance"],
            "vip_allowed": False,
            "regions": ["ural", "volga"],
        },
    },
    {
        "executor_id": "executor-03",
        "active": True,
        "capacity": 1.5,
        "daily_limit": 80,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 1500000,
            "client_msp": ["small", "medium", "large"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW", "CONSULTATION"],
            "subjects": ["contract", "claims"],
            "vip_allowed": True,
            "regions": ["siberia", "central"],
        },
    },
    {
        "executor_id": "executor-04",
        "active": True,
        "capacity": 1.5,
        "daily_limit": 75,
        "attributes": {
            "min_accept_sum": 100000,
            "max_accept_sum": 2000000,
            "client_msp": ["large"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW", "CLAIM_PROCESSING"],
            "subjects": ["claims", "compliance"],
            "vip_allowed": True,
            "regions": ["central", "south"],
        },
    },
    {
        "executor_id": "executor-05",
        "active": True,
        "capacity": 2.0,
        "daily_limit": 100,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 5000000,
            "client_msp": ["small", "medium", "large"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW", "CONSULTATION", "CLAIM_PROCESSING"],
            "subjects": ["contract", "claims", "payments", "compliance"],
            "vip_allowed": True,
            "regions": ["ural", "siberia", "central", "volga", "south"],
        },
    },
    {
        "executor_id": "executor-06",
        "active": True,
        "capacity": 0.5,
        "daily_limit": 30,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 300000,
            "client_msp": ["small"],
            "executor_msp": ["consulting"],
            "order_types": ["CONSULTATION"],
            "subjects": ["payments"],
            "vip_allowed": False,
            "regions": ["volga"],
        },
    },
    {
        "executor_id": "executor-07",
        "active": True,
        "capacity": 0.5,
        "daily_limit": 35,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 400000,
            "client_msp": ["small", "medium"],
            "executor_msp": ["consulting"],
            "order_types": ["CONSULTATION"],
            "subjects": ["payments", "compliance"],
            "vip_allowed": False,
            "regions": ["south", "central"],
        },
    },
    {
        "executor_id": "executor-08",
        "active": True,
        "capacity": 1.0,
        "daily_limit": None,  # Unlimited
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 1000000,
            "client_msp": ["small", "medium"],
            "executor_msp": ["claims_dept"],
            "order_types": ["CLAIM_PROCESSING"],
            "subjects": ["claims"],
            "vip_allowed": False,
            "regions": ["ural", "siberia"],
        },
    },
    {
        "executor_id": "executor-09",
        "active": True,
        "capacity": 1.5,
        "daily_limit": None,  # Unlimited
        "attributes": {
            "min_accept_sum": 50000,
            "max_accept_sum": 2500000,
            "client_msp": ["medium", "large"],
            "executor_msp": ["claims_dept"],
            "order_types": ["CLAIM_PROCESSING"],
            "subjects": ["claims", "payments"],
            "vip_allowed": True,
            "regions": ["central", "volga"],
        },
    },
    {
        "executor_id": "executor-10",
        "active": True,
        "capacity": 2.0,
        "daily_limit": 120,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 10000000,
            "client_msp": ["small", "medium", "large"],
            "executor_msp": ["claims_dept"],
            "order_types": ["CLAIM_PROCESSING", "LEGAL_REVIEW"],
            "subjects": ["claims", "contract"],
            "vip_allowed": True,
            "regions": ["ural", "central", "south"],
        },
    },
    {
        "executor_id": "executor-11",
        "active": True,
        "capacity": 1.0,
        "daily_limit": 70,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 800000,
            "client_msp": ["small", "medium"],
            "executor_msp": ["consulting"],
            "order_types": ["CONSULTATION"],
            "subjects": ["compliance"],
            "vip_allowed": False,
            "regions": ["siberia"],
        },
    },
    {
        "executor_id": "executor-12",
        "active": True,
        "capacity": 1.0,
        "daily_limit": 50,
        "attributes": {
            "min_accept_sum": 10000,
            "max_accept_sum": 600000,
            "client_msp": ["small"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW"],
            "subjects": ["contract"],
            "vip_allowed": False,
            "regions": ["volga", "south"],
        },
    },
    {
        "executor_id": "executor-13",
        "active": True,
        "capacity": 1.5,
        "daily_limit": 90,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 3000000,
            "client_msp": ["medium", "large"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW", "CONSULTATION"],
            "subjects": ["contract", "payments"],
            "vip_allowed": True,
            "regions": ["central", "ural"],
        },
    },
    {
        "executor_id": "executor-14",
        "active": True,
        "capacity": 2.0,
        "daily_limit": None,  # Unlimited
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 5000000,
            "client_msp": ["large"],
            "executor_msp": ["legal", "claims_dept"],
            "order_types": ["LEGAL_REVIEW", "CLAIM_PROCESSING"],
            "subjects": ["claims", "compliance"],
            "vip_allowed": True,
            "regions": ["central", "siberia", "volga"],
        },
    },
    {
        "executor_id": "executor-15",
        "active": True,
        "capacity": 0.5,
        "daily_limit": 40,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 500000,
            "client_msp": ["small"],
            "executor_msp": ["consulting"],
            "order_types": ["CONSULTATION"],
            "subjects": ["payments"],
            "vip_allowed": False,
            "regions": ["south"],
        },
    },
    {
        "executor_id": "executor-16",
        "active": True,
        "capacity": 1.0,
        "daily_limit": 60,
        "attributes": {
            "min_accept_sum": 50000,
            "max_accept_sum": 900000,
            "client_msp": ["small", "medium"],
            "executor_msp": ["claims_dept"],
            "order_types": ["CLAIM_PROCESSING"],
            "subjects": ["claims", "payments"],
            "vip_allowed": False,
            "regions": ["ural"],
        },
    },
    {
        "executor_id": "executor-17",
        "active": True,
        "capacity": 1.5,
        "daily_limit": 80,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 2000000,
            "client_msp": ["medium", "large"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW", "CONSULTATION"],
            "subjects": ["contract", "compliance"],
            "vip_allowed": True,
            "regions": ["central", "south"],
        },
    },
    {
        "executor_id": "executor-18",
        "active": True,
        "capacity": 1.0,
        "daily_limit": 50,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 700000,
            "client_msp": ["small", "medium"],
            "executor_msp": ["consulting"],
            "order_types": ["CONSULTATION", "CLAIM_PROCESSING"],
            "subjects": ["payments", "claims"],
            "vip_allowed": False,
            "regions": ["volga", "siberia"],
        },
    },
    {
        "executor_id": "executor-19",
        "active": False,  # Inactive by default for test scenarios
        "capacity": 1.0,
        "daily_limit": 50,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 1000000,
            "client_msp": ["small", "medium"],
            "executor_msp": ["legal"],
            "order_types": ["LEGAL_REVIEW"],
            "subjects": ["contract"],
            "vip_allowed": False,
            "regions": ["ural"],
        },
    },
    {
        "executor_id": "executor-20",
        "active": False,  # Inactive by default for test scenarios
        "capacity": 1.5,
        "daily_limit": 100,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 2000000,
            "client_msp": ["large"],
            "executor_msp": ["claims_dept"],
            "order_types": ["CLAIM_PROCESSING"],
            "subjects": ["claims"],
            "vip_allowed": True,
            "regions": ["central"],
        },
    },
    {
        "executor_id": "executor-21",
        "active": True,
        "capacity": 2.0,
        "daily_limit": 150,
        "attributes": {
            "min_accept_sum": 0,
            "max_accept_sum": 10000000,
            "client_msp": ["small", "medium", "large"],
            "executor_msp": ["legal", "consulting", "claims_dept"],
            "order_types": ["LEGAL_REVIEW", "CONSULTATION", "CLAIM_PROCESSING"],
            "subjects": ["contract", "claims", "payments", "compliance"],
            "vip_allowed": True,
            "regions": ["ural", "siberia", "central", "volga", "south"],
        },
    },
]


async def seed_database(session: AsyncSession, seed_orders: bool = False):
    repo = ExecutorRepository(session)
    count = await repo.count_executors()
    if count < len(PRESET_EXECUTORS):
        logger.info(f"Seeding {len(PRESET_EXECUTORS)} preset executors...")
        for item in PRESET_EXECUTORS:
            existing = await repo.get_by_id(item["executor_id"])
            if not existing:
                row = await repo.create(
                    executor_id=item["executor_id"],
                    active=item["active"],
                    capacity=item["capacity"],
                    daily_limit=item["daily_limit"],
                    attributes=item["attributes"],
                    version=1,
                )
                await kafka_producer.publish_executor_created(row.to_dict())
        logger.info("Executor seeding complete.")
    else:
        logger.info(f"Database already seeded with {count} executors.")

    if seed_orders:
        order_repo = OrderRepository(session)
        order_count = await order_repo.count_orders()
        if order_count < 10000:
            logger.info(f"Database has {order_count} orders (< 10000). Populating 10,000 realistic orders...")
            from .populate_10k import generate_10k_orders_data
            orders_data = generate_10k_orders_data()
            chunk_size = 500
            for idx in range(0, len(orders_data), chunk_size):
                chunk = orders_data[idx : idx + chunk_size]
                await order_repo.bulk_create(chunk)
            logger.info("10,000 realistic orders populated in database.")
        else:
            logger.info(f"Database already contains {order_count} orders.")
