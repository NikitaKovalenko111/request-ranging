import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone, timedelta

from pathlib import Path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from simulation.app.storage.database import async_session_factory, init_db, engine, Base
from simulation.app.storage.tables import OrderRow, ExecutorRow, now_iso
from simulation.app.generator.seeds import PRESET_EXECUTORS

logger = logging.getLogger("ais.populate")

TEXTS_BY_SUBJECT = {
    "contract": [
        "Срочная правовая экспертиза договора поставки промышленного оборудования",
        "Согласование протокола разногласий к договору аренды коммерческой недвижимости",
        "Анализ лицензионного соглашения на программное обеспечение и рисков исключительных прав",
        "Проверка рамочного соглашения о дистрибуции и логистике на территории РФ",
        "Аудит договора генерального подряда на строительство производственного цеха",
        "Анализ соглашения о конфиденциальности (NDA) при стратегическом партнерстве",
        "Разработка внешнеторгового контракта с нерезидентом в дружественной юрисдикции",
        "Экспертиза дополнительного соглашения об изменении графика платежей и поставок",
        "Проверка типового договора оказания услуг на предмет кабальных условий",
        "Согласование условий долгосрочного договора лизинга спецтехники",
    ],
    "claims": [
        "Подготовка мотивированного ответа на досудебную претензию контрагента по неустойке",
        "Претензионная работа по факту выявления скрытых дефектов партии оборудования",
        "Подготовка досудебной претензии о взыскании задолженности по актам выполненных работ",
        "Анализ претензии заказчика о нарушении сроков оказания IT-услуг",
        "Урегулирование спорной ситуации при одностороннем отказе от исполнения договора",
        "Формирование пакета документов для подачи судебного иска о возмещении убытков",
        "Оценка перспектив судебного разбирательства по иску о ненадлежащем качестве услуг",
        "Претензия транспортной компании по факту утраты груза при мультимодальной перевозке",
        "Подготовка отзыва на исковое заявление о взыскании штрафных санкций",
    ],
    "payments": [
        "Консультация по валютному контролю при экспортных расчетах с контрагентом",
        "Правовой анализ требований комплаенс и финмониторинга банка по 115-ФЗ",
        "Согласование условий расчетов с использованием аккредитива и эскроу-счетов",
        "Анализ условий предоставления банковской гарантии для государственного контракта",
        "Консультация по налоговым последствиям уступки прав денежного требования (цессия)",
        "Проверка договора факторинга и передачи будущих денежных потоков",
        "Экспертиза графика платежей по инвестиционному кредитному соглашению",
    ],
    "compliance": [
        "Комплексная проверка контрагента на благонадежность и налоговые риски (Due Diligence)",
        "Аудит локальных нормативных актов на соответствие трудовому законодательству",
        "Оценка рисков привлечения к субсидиарной ответственности контролирующих лиц",
        "Разработка антикоррупционной политики и кодекса деловой этики предприятия",
        "Проверка соответствия порядка обработки персональных данных требованиям 152-ФЗ",
        "Консультация по санкционным ограничениям и рискам вторичных санкций",
        "Аудит положений о коммерческой тайне и режима защиты конфиденциальной информации",
    ],
}

SUBJECT_TO_TYPE = {
    "contract": ["LEGAL_REVIEW", "CONSULTATION"],
    "claims": ["CLAIM_PROCESSING", "LEGAL_REVIEW"],
    "payments": ["CONSULTATION", "CLAIM_PROCESSING"],
    "compliance": ["LEGAL_REVIEW", "CONSULTATION"],
}

REGIONS = ["ural", "siberia", "central", "volga", "south", "northwest"]
CLIENT_MSPS = ["small", "medium", "large"]
EXECUTOR_MSPS = ["legal", "consulting", "claims_dept"]


def generate_10k_orders_data() -> list:
    random.seed(42)  # Deterministic high-quality generation
    orders = []
    base_time = datetime(2026, 9, 25, 8, 0, 0, tzinfo=timezone.utc)

    # 1. First 400 orders: status='await' (returned for rework)
    for i in range(1, 401):
        order_id = f"order-{i:05d}"
        subject = random.choice(["contract", "claims", "payments", "compliance"])
        order_type = random.choice(SUBJECT_TO_TYPE[subject])
        client_msp = random.choices(["small", "medium", "large"], weights=[50, 35, 15])[0]
        
        if client_msp == "small":
            order_sum = random.randint(50_000, 450_000)
            vip = False
            weight = random.choice([0.5, 0.8, 1.0])
        elif client_msp == "medium":
            order_sum = random.randint(500_000, 2_000_000)
            vip = random.random() < 0.2
            weight = random.choice([1.0, 1.2, 1.5])
        else:
            order_sum = random.randint(2_500_000, 15_000_000)
            vip = random.random() < 0.5
            weight = random.choice([1.5, 1.8, 2.0])

        created_dt = base_time + timedelta(seconds=i * 12)
        created_str = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        attrs = {
            "sum": order_sum,
            "order_type": order_type,
            "subject": subject,
            "vip": vip,
            "client_msp": client_msp,
            "executor_msp": random.choice(EXECUTOR_MSPS),
            "text": random.choice(TEXTS_BY_SUBJECT[subject]),
            "region": random.choice(REGIONS),
        }

        orders.append({
            "order_id": order_id,
            "parent_id": None,
            "status": "await",
            "weight": weight,
            "version": 2,
            "attributes": attrs,
            "created_at": created_str,
            "updated_at": created_str,
        })

    # 2. Next 600 orders: status='processed' WITH parent_id linking to the await orders
    for i in range(401, 1001):
        order_id = f"order-{i:05d}"
        parent_num = random.randint(1, 400)
        parent_id = f"order-{parent_num:05d}"

        subject = random.choice(["contract", "claims", "payments", "compliance"])
        order_type = random.choice(SUBJECT_TO_TYPE[subject])
        client_msp = random.choices(["small", "medium", "large"], weights=[45, 35, 20])[0]

        if client_msp == "small":
            order_sum = random.randint(60_000, 480_000)
            vip = False
            weight = random.choice([0.5, 0.8, 1.0])
        elif client_msp == "medium":
            order_sum = random.randint(550_000, 2_200_000)
            vip = random.random() < 0.25
            weight = random.choice([1.0, 1.2, 1.5])
        else:
            order_sum = random.randint(3_000_000, 18_000_000)
            vip = random.random() < 0.55
            weight = random.choice([1.5, 1.8, 2.0])

        created_dt = base_time + timedelta(seconds=i * 10)
        created_str = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        attrs = {
            "sum": order_sum,
            "order_type": order_type,
            "subject": subject,
            "vip": vip,
            "client_msp": client_msp,
            "executor_msp": random.choice(EXECUTOR_MSPS),
            "text": f"Повторное рассмотрение после доработки: {random.choice(TEXTS_BY_SUBJECT[subject])}",
            "region": random.choice(REGIONS),
        }

        orders.append({
            "order_id": order_id,
            "parent_id": parent_id,
            "status": "processed",
            "weight": weight,
            "version": 1,
            "attributes": attrs,
            "created_at": created_str,
            "updated_at": created_str,
        })

    # 3. Next 150 orders: status='accept' (already completed history)
    for i in range(1001, 1151):
        order_id = f"order-{i:05d}"
        subject = random.choice(["contract", "claims", "payments", "compliance"])
        order_type = random.choice(SUBJECT_TO_TYPE[subject])
        client_msp = random.choices(["small", "medium", "large"], weights=[50, 30, 20])[0]
        order_sum = random.randint(100_000, 3_000_000)
        vip = random.random() < 0.2
        weight = random.choice([0.8, 1.0, 1.5, 2.0])

        created_dt = base_time + timedelta(seconds=i * 8)
        created_str = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        orders.append({
            "order_id": order_id,
            "parent_id": None,
            "status": "accept",
            "weight": weight,
            "version": 2,
            "attributes": {
                "sum": order_sum,
                "order_type": order_type,
                "subject": subject,
                "vip": vip,
                "client_msp": client_msp,
                "executor_msp": random.choice(EXECUTOR_MSPS),
                "text": random.choice(TEXTS_BY_SUBJECT[subject]),
                "region": random.choice(REGIONS),
            },
            "created_at": created_str,
            "updated_at": created_str,
        })

    # 4. Next 50 orders: status='reject' (rejected history)
    for i in range(1151, 1201):
        order_id = f"order-{i:05d}"
        subject = random.choice(["contract", "claims", "payments", "compliance"])
        order_type = random.choice(SUBJECT_TO_TYPE[subject])
        order_sum = random.randint(100_000, 2_000_000)
        created_dt = base_time + timedelta(seconds=i * 8)
        created_str = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        orders.append({
            "order_id": order_id,
            "parent_id": None,
            "status": "reject",
            "weight": 1.0,
            "version": 2,
            "attributes": {
                "sum": order_sum,
                "order_type": order_type,
                "subject": subject,
                "vip": False,
                "client_msp": "small",
                "executor_msp": "legal",
                "text": random.choice(TEXTS_BY_SUBJECT[subject]),
                "region": random.choice(REGIONS),
            },
            "created_at": created_str,
            "updated_at": created_str,
        })

    # 5. Remaining 8,800 orders (1201 to 10000): status='processed' READY FOR BALANCING!
    for i in range(1201, 10001):
        order_id = f"order-{i:05d}"
        subject = random.choice(["contract", "claims", "payments", "compliance"])
        order_type = random.choice(SUBJECT_TO_TYPE[subject])
        client_msp = random.choices(["small", "medium", "large"], weights=[45, 35, 20])[0]

        if client_msp == "small":
            order_sum = random.randint(50_000, 450_000)
            vip = False
            weight = random.choice([0.5, 0.8, 1.0])
        elif client_msp == "medium":
            order_sum = random.randint(500_000, 2_000_000)
            vip = random.random() < 0.22
            weight = random.choice([1.0, 1.2, 1.5, 1.8])
        else:
            order_sum = random.randint(2_500_000, 20_000_000)
            vip = random.random() < 0.50
            weight = random.choice([1.5, 1.8, 2.0])

        created_dt = base_time + timedelta(seconds=i * 6)
        created_str = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        attrs = {
            "sum": order_sum,
            "order_type": order_type,
            "subject": subject,
            "vip": vip,
            "client_msp": client_msp,
            "executor_msp": random.choice(EXECUTOR_MSPS),
            "text": random.choice(TEXTS_BY_SUBJECT[subject]),
            "region": random.choice(REGIONS),
        }

        orders.append({
            "order_id": order_id,
            "parent_id": None,
            "status": "processed",
            "weight": weight,
            "version": 1,
            "attributes": attrs,
            "created_at": created_str,
            "updated_at": created_str,
        })

    return orders


async def populate_database():
    start_time = time.time()
    print("Initializing tables...")
    await init_db()

    # Recreate tables to have clean pristine database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tables dropped and re-created.")

    # 1. Seed Executors
    print(f"Seeding {len(PRESET_EXECUTORS)} executors...")
    async with async_session_factory() as session:
        exec_rows = [
            ExecutorRow(
                executor_id=e["executor_id"],
                active=e["active"],
                capacity=e["capacity"],
                daily_limit=e.get("daily_limit"),
                version=1,
                skills_json=json.dumps(e.get("skills", []), ensure_ascii=False),
                attributes_json=json.dumps(e["attributes"], ensure_ascii=False),
                created_at=now_iso(),
                updated_at=now_iso(),
            )
            for e in PRESET_EXECUTORS
        ]
        session.add_all(exec_rows)
        await session.commit()
    print("Executors seeded.")

    # 2. Generate and Insert 10,000 Orders
    print("Generating 10,000 realistic orders with Russian business attributes...")
    orders_data = generate_10k_orders_data()
    print(f"Generated {len(orders_data)} orders in memory. Inserting into SQLite...")

    chunk_size = 500
    total = len(orders_data)
    for idx in range(0, total, chunk_size):
        chunk = orders_data[idx : idx + chunk_size]
        async with async_session_factory() as session:
            rows = [
                OrderRow(
                    order_id=o["order_id"],
                    parent_id=o.get("parent_id"),
                    status=o.get("status", "processed"),
                    weight=o.get("weight", 1.0),
                    version=o.get("version", 1),
                    attributes_json=json.dumps(o.get("attributes", {}), ensure_ascii=False),
                    created_at=o["created_at"],
                    updated_at=o["updated_at"],
                )
                for o in chunk
            ]
            session.add_all(rows)
            await session.commit()
        print(f"Inserted orders {idx + len(chunk)}/{total}...", end="\r")

    elapsed = time.time() - start_time
    print(f"\nDone! Successfully populated 10,000 orders in {elapsed:.2f} seconds.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(populate_database())
