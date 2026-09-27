import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.order import Order, OrderCreate, OrderPatch
from ..storage.database import get_db_session
from ..storage.repository import OrderRepository
from ..kafka.producer import kafka_producer

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = OrderRepository(session)
    order_id = payload.order_id or f"order-{uuid.uuid4().hex[:8]}"
    
    # Check duplicate
    existing = await repo.get_by_id(order_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ORDER_ALREADY_EXISTS", "message": f"Order {order_id} already exists", "retryable": False},
        )

    row = await repo.create(
        order_id=order_id,
        parent_id=payload.parent_id,
        status=payload.status.value,
        weight=payload.weight,
        attributes=payload.attributes.model_dump(),
        version=1,
    )
    order_dict = row.to_dict()
    await kafka_producer.publish_order_created(order_dict)
    return Order(**order_dict)


@router.get("", response_model=List[Order])
async def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
):
    repo = OrderRepository(session)
    rows = await repo.list_orders(status=status_filter, limit=limit, offset=offset)
    return [Order(**r.to_dict()) for r in rows]


@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    repo = OrderRepository(session)
    row = await repo.get_by_id(order_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORDER_NOT_FOUND", "message": f"Order {order_id} not found", "retryable": False},
        )
    return Order(**row.to_dict())


@router.patch("/{order_id}", response_model=Order)
async def patch_order(
    order_id: str,
    payload: OrderPatch,
    session: AsyncSession = Depends(get_db_session),
):
    repo = OrderRepository(session)
    row, param_changed, status_changed, prev_status, updated_order_dict = await repo.update_order(
        order_id=order_id,
        new_status=payload.status.value if payload.status else None,
        new_weight=payload.weight,
        new_attributes=payload.attributes,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORDER_NOT_FOUND", "message": f"Order {order_id} not found", "retryable": False},
        )

    order_dict = row.to_dict()

    # Publish events according to contract
    if param_changed and not status_changed:
        await kafka_producer.publish_order_updated(order_dict)
    elif status_changed and not param_changed:
        await kafka_producer.publish_order_status_changed(
            order_id=order_id,
            previous_status=prev_status or "processed",
            status=row.status,
            version=row.version,
        )
    elif param_changed and status_changed:
        # Both changed: sequential versions (V then V+1)
        await kafka_producer.publish_order_updated(updated_order_dict)
        await kafka_producer.publish_order_status_changed(
            order_id=order_id,
            previous_status=prev_status or "processed",
            status=row.status,
            version=row.version,
        )

    return Order(**order_dict)
