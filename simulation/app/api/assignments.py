import asyncio
import random
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.assignment import AssignmentRequest, AssignmentResponse, AssignmentError
from ..models.event import get_current_rfc3339
from ..storage.database import get_db_session
from ..storage.repository import OrderRepository, ExecutorRepository, AssignmentRepository

router = APIRouter(prefix="/api/v1/assignments", tags=["Assignments"])


@router.post(
    "",
    response_model=AssignmentResponse,
    responses={
        400: {"model": AssignmentError},
        404: {"model": AssignmentError},
        409: {"model": AssignmentError},
        422: {"model": AssignmentError},
    },
)
async def create_assignment(
    payload: AssignmentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_db_session),
):
    assignment_repo = AssignmentRepository(session)
    order_repo = OrderRepository(session)
    executor_repo = ExecutorRepository(session)

    # 1. Check idempotency: if assignment_id already exists, return same result immediately
    existing_assignment = await assignment_repo.get_by_id(payload.assignment_id)
    if existing_assignment:
        return AssignmentResponse(
            assignment_id=existing_assignment.assignment_id,
            order_id=existing_assignment.order_id,
            executor_id=existing_assignment.executor_id,
            status=existing_assignment.status,
            confirmed_at=existing_assignment.confirmed_at or get_current_rfc3339(),
        )

    # 2. Check Order existence
    order = await order_repo.get_by_id(payload.order_id)
    if not order:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=AssignmentError(
                code="ORDER_NOT_FOUND",
                message=f"Order {payload.order_id} not found",
                retryable=False,
            ).model_dump(),
        )

    # 3. Check if Order is already assigned to a different executor
    existing_order_assignment = await assignment_repo.get_by_order_id(payload.order_id)
    if existing_order_assignment and existing_order_assignment.assignment_id != payload.assignment_id:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=AssignmentError(
                code="ORDER_ALREADY_ASSIGNED",
                message=f"Order {payload.order_id} is already assigned to executor {existing_order_assignment.executor_id}",
                retryable=False,
            ).model_dump(),
        )

    # 4. Check Executor existence and active status
    executor = await executor_repo.get_by_id(payload.executor_id)
    if not executor:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=AssignmentError(
                code="EXECUTOR_NOT_FOUND",
                message=f"Executor {payload.executor_id} not found",
                retryable=False,
            ).model_dump(),
        )

    if not executor.active:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=AssignmentError(
                code="EXECUTOR_INACTIVE",
                message=f"Executor {payload.executor_id} is inactive",
                retryable=False,
            ).model_dump(),
        )

    # 5. Check order status allows assignment (only 'processed' is allowed)
    if order.status not in ("processed",):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=AssignmentError(
                code="INVALID_ORDER_STATUS",
                message=f"Order {payload.order_id} is in status '{order.status}', assignment forbidden",
                retryable=False,
            ).model_dump(),
        )

    # 6. Simulate external AIS processing delay (contract: 2 to 10 seconds)
    if settings.assignment_delay_max > 0:
        delay = random.uniform(settings.assignment_delay_min, settings.assignment_delay_max)
        await asyncio.sleep(delay)

    # 7. Persist assignment and link to order
    confirmed_at = get_current_rfc3339()
    created_assignment = await assignment_repo.create(
        assignment_id=payload.assignment_id,
        order_id=payload.order_id,
        executor_id=payload.executor_id,
        decided_at=payload.decided_at,
        confirmed_at=confirmed_at,
        status="confirmed",
    )
    await order_repo.assign_executor(payload.order_id, payload.executor_id)

    return AssignmentResponse(
        assignment_id=created_assignment.assignment_id,
        order_id=created_assignment.order_id,
        executor_id=created_assignment.executor_id,
        status="confirmed",
        confirmed_at=confirmed_at,
    )
