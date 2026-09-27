import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from .tables import OrderRow, ExecutorRow, AssignmentRow, now_iso


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: str) -> Optional[OrderRow]:
        res = await self.session.execute(select(OrderRow).where(OrderRow.order_id == order_id))
        return res.scalar_one_or_none()

    async def create(
        self,
        order_id: str,
        parent_id: Optional[str],
        status: str,
        weight: float,
        attributes: Dict[str, Any],
        version: int = 1,
    ) -> OrderRow:
        row = OrderRow(
            order_id=order_id,
            parent_id=parent_id,
            status=status,
            weight=weight,
            version=version,
            attributes_json=json.dumps(attributes, ensure_ascii=False),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def bulk_create(self, orders: List[Dict[str, Any]]) -> List[OrderRow]:
        """High-performance batch insert for burst generation (e.g. 1k burst, 10k total)."""
        now = now_iso()
        rows = [
            OrderRow(
                order_id=o["order_id"],
                parent_id=o.get("parent_id"),
                status=o.get("status", "processed"),
                weight=o.get("weight", 1.0),
                version=o.get("version", 1),
                attributes_json=json.dumps(o.get("attributes", {}), ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
            for o in orders
        ]
        self.session.add_all(rows)
        await self.session.commit()
        return rows

    async def list_orders(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[OrderRow]:
        query = select(OrderRow)
        if status:
            query = query.where(OrderRow.status == status)
        query = query.order_by(OrderRow.created_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def count_orders(self, status: Optional[str] = None) -> int:
        query = select(func.count(OrderRow.order_id))
        if status:
            query = query.where(OrderRow.status == status)
        res = await self.session.execute(query)
        return res.scalar_one() or 0

    async def update_order(
        self,
        order_id: str,
        new_status: Optional[str] = None,
        new_weight: Optional[float] = None,
        new_attributes: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[OrderRow], bool, bool, Optional[str]]:
        row = await self.get_by_id(order_id)
        if not row:
            return None, False, False, None

        has_param_changed = False
        has_status_changed = False
        prev_status = row.status

        if new_weight is not None and new_weight != row.weight:
            row.weight = new_weight
            has_param_changed = True

        if new_attributes is not None:
            current_attrs = json.loads(row.attributes_json) if row.attributes_json else {}
            current_attrs.update(new_attributes)
            row.attributes_json = json.dumps(current_attrs, ensure_ascii=False)
            has_param_changed = True

        if new_status is not None and new_status != row.status:
            row.status = new_status
            has_status_changed = True

        if has_param_changed or has_status_changed:
            row.version += 1
            row.updated_at = now_iso()
            await self.session.commit()
            await self.session.refresh(row)

        return row, has_param_changed, has_status_changed, prev_status

    async def assign_executor(self, order_id: str, executor_id: str) -> Optional[OrderRow]:
        row = await self.get_by_id(order_id)
        if not row:
            return None
        row.assigned_executor_id = executor_id
        row.updated_at = now_iso()
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get_random_orders(self, status: str = "processed", limit: int = 20) -> List[OrderRow]:
        query = select(OrderRow).where(OrderRow.status == status).order_by(func.random()).limit(limit)
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def get_await_order_ids(self, limit: int = 50) -> List[str]:
        query = select(OrderRow.order_id).where(OrderRow.status == "await").limit(limit)
        res = await self.session.execute(query)
        return list(res.scalars().all())


class ExecutorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, executor_id: str) -> Optional[ExecutorRow]:
        res = await self.session.execute(select(ExecutorRow).where(ExecutorRow.executor_id == executor_id))
        return res.scalar_one_or_none()

    async def create(
        self,
        executor_id: str,
        active: bool,
        capacity: float,
        daily_limit: Optional[int],
        attributes: Dict[str, Any],
        version: int = 1,
    ) -> ExecutorRow:
        row = ExecutorRow(
            executor_id=executor_id,
            active=active,
            capacity=capacity,
            daily_limit=daily_limit,
            version=version,
            attributes_json=json.dumps(attributes, ensure_ascii=False),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def bulk_create(self, executors: List[Dict[str, Any]]) -> List[ExecutorRow]:
        now = now_iso()
        rows = [
            ExecutorRow(
                executor_id=e["executor_id"],
                active=e.get("active", True),
                capacity=e.get("capacity", 1.0),
                daily_limit=e.get("daily_limit"),
                version=e.get("version", 1),
                attributes_json=json.dumps(e.get("attributes", {}), ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
            for e in executors
        ]
        self.session.add_all(rows)
        await self.session.commit()
        return rows

    async def list_executors(
        self,
        active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExecutorRow]:
        query = select(ExecutorRow)
        if active is not None:
            query = query.where(ExecutorRow.active == active)
        query = query.order_by(ExecutorRow.executor_id.asc()).limit(limit).offset(offset)
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def count_executors(self, active: Optional[bool] = None) -> int:
        query = select(func.count(ExecutorRow.executor_id))
        if active is not None:
            query = query.where(ExecutorRow.active == active)
        res = await self.session.execute(query)
        return res.scalar_one() or 0

    async def update_executor(
        self,
        executor_id: str,
        active: Optional[bool] = None,
        capacity: Optional[float] = None,
        daily_limit: Optional[int] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExecutorRow]:
        row = await self.get_by_id(executor_id)
        if not row:
            return None

        changed = False
        if active is not None and active != row.active:
            row.active = active
            changed = True
        if capacity is not None and capacity != row.capacity:
            row.capacity = capacity
            changed = True
        if daily_limit is not None and daily_limit != row.daily_limit:
            row.daily_limit = daily_limit
            changed = True
        if attributes is not None:
            current_attrs = json.loads(row.attributes_json) if row.attributes_json else {}
            current_attrs.update(attributes)
            row.attributes_json = json.dumps(current_attrs, ensure_ascii=False)
            changed = True

        if changed:
            row.version += 1
            row.updated_at = now_iso()
            await self.session.commit()
            await self.session.refresh(row)

        return row


class AssignmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, assignment_id: str) -> Optional[AssignmentRow]:
        res = await self.session.execute(
            select(AssignmentRow).where(AssignmentRow.assignment_id == assignment_id)
        )
        return res.scalar_one_or_none()

    async def get_by_order_id(self, order_id: str) -> Optional[AssignmentRow]:
        res = await self.session.execute(
            select(AssignmentRow).where(AssignmentRow.order_id == order_id)
        )
        return res.scalar_one_or_none()

    async def create(
        self,
        assignment_id: str,
        order_id: str,
        executor_id: str,
        decided_at: str,
        confirmed_at: str,
        status: str = "confirmed",
    ) -> AssignmentRow:
        row = AssignmentRow(
            assignment_id=assignment_id,
            order_id=order_id,
            executor_id=executor_id,
            decided_at=decided_at,
            confirmed_at=confirmed_at,
            status=status,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def count_assignments(self) -> int:
        res = await self.session.execute(select(func.count(AssignmentRow.assignment_id)))
        return res.scalar_one() or 0
