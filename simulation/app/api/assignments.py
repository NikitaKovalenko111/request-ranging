import asyncio
import random
from typing import Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.assignment import AssignmentRequest, AssignmentResponse, AssignmentError
from ..models.event import get_current_rfc3339
from ..storage.database import get_db_session
from ..storage.repository import OrderRepository, ExecutorRepository, AssignmentRepository

router = APIRouter(prefix="/api/v1/assignments", tags=["Assignments"])

# In-flight concurrency tracking to prevent race conditions during delay
_in_flight_orders: Dict[str, asyncio.Future] = {}
_in_flight_assignments: Dict[str, asyncio.Future] = {}
_assignment_lock = asyncio.Lock()


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
    # 0. Enforce Idempotency-Key header presence and matching with assignment_id
    if not idempotency_key or idempotency_key != payload.assignment_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AssignmentError(
                code="INVALID_IDEMPOTENCY_KEY",
                message="Idempotency-Key header is required and must match assignment_id",
                retryable=False,
            ).model_dump(),
        )

    # 1. In-flight concurrency coordination
    is_leader = False
    follower_future: Optional[asyncio.Future] = None

    async with _assignment_lock:
        if payload.assignment_id in _in_flight_assignments:
            # Exact same assignment_id is currently in-flight: wait on its result
            follower_future = _in_flight_assignments[payload.assignment_id]
        elif payload.order_id in _in_flight_orders:
            # Order is already currently being assigned by another concurrent request!
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=AssignmentError(
                    code="ORDER_ALREADY_ASSIGNED",
                    message=f"Order {payload.order_id} is currently being assigned",
                    retryable=False,
                ).model_dump(),
            )
        else:
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            _in_flight_orders[payload.order_id] = future
            _in_flight_assignments[payload.assignment_id] = future
            is_leader = True

    if not is_leader and follower_future is not None:
        return await follower_future

    assignment_repo = AssignmentRepository(session)
    order_repo = OrderRepository(session)
    executor_repo = ExecutorRepository(session)

    try:
        # 2. Check idempotency: if assignment_id already exists in DB, return same result immediately
        existing_assignment = await assignment_repo.get_by_id(payload.assignment_id)
        if existing_assignment:
            res = AssignmentResponse(
                assignment_id=existing_assignment.assignment_id,
                order_id=existing_assignment.order_id,
                executor_id=existing_assignment.executor_id,
                status=existing_assignment.status,
                confirmed_at=existing_assignment.confirmed_at or get_current_rfc3339(),
            )
            future.set_result(res)
            return res

        # 3. Check Order existence
        order = await order_repo.get_by_id(payload.order_id)
        if not order:
            res = JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=AssignmentError(
                    code="ORDER_NOT_FOUND",
                    message=f"Order {payload.order_id} not found",
                    retryable=False,
                ).model_dump(),
            )
            future.set_result(res)
            return res

        # 4. Check if Order is already assigned to a different executor in DB
        existing_order_assignment = await assignment_repo.get_by_order_id(payload.order_id)
        if existing_order_assignment and existing_order_assignment.assignment_id != payload.assignment_id:
            res = JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=AssignmentError(
                    code="ORDER_ALREADY_ASSIGNED",
                    message=f"Order {payload.order_id} is already assigned to executor {existing_order_assignment.executor_id}",
                    retryable=False,
                ).model_dump(),
            )
            future.set_result(res)
            return res

        # 5. Check Executor existence and active status
        executor = await executor_repo.get_by_id(payload.executor_id)
        if not executor:
            res = JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=AssignmentError(
                    code="EXECUTOR_NOT_FOUND",
                    message=f"Executor {payload.executor_id} not found",
                    retryable=False,
                ).model_dump(),
            )
            future.set_result(res)
            return res

        if not executor.active:
            res = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=AssignmentError(
                    code="EXECUTOR_INACTIVE",
                    message=f"Executor {payload.executor_id} is inactive",
                    retryable=False,
                ).model_dump(),
            )
            future.set_result(res)
            return res

        # 6. Check order status allows assignment (only 'processed' is allowed)
        if order.status not in ("processed",):
            res = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=AssignmentError(
                    code="INVALID_ORDER_STATUS",
                    message=f"Order {payload.order_id} is in status '{order.status}', assignment forbidden",
                    retryable=False,
                ).model_dump(),
            )
            future.set_result(res)
            return res

        # 7. Simulate external AIS processing delay (contract: 2 to 10 seconds)
        if settings.assignment_delay_max > 0:
            delay = random.uniform(settings.assignment_delay_min, settings.assignment_delay_max)
            await asyncio.sleep(delay)

        # 8. Persist assignment and link to order with DB IntegrityError protection
        confirmed_at = get_current_rfc3339()
        try:
            created_assignment = await assignment_repo.create(
                assignment_id=payload.assignment_id,
                order_id=payload.order_id,
                executor_id=payload.executor_id,
                decided_at=payload.decided_at,
                confirmed_at=confirmed_at,
                status="confirmed",
            )
            await order_repo.assign_executor(payload.order_id, payload.executor_id)
            res = AssignmentResponse(
                assignment_id=created_assignment.assignment_id,
                order_id=created_assignment.order_id,
                executor_id=created_assignment.executor_id,
                status="confirmed",
                confirmed_at=confirmed_at,
            )
        except IntegrityError:
            await session.rollback()
            existing_assignment = await assignment_repo.get_by_id(payload.assignment_id)
            if existing_assignment:
                res = AssignmentResponse(
                    assignment_id=existing_assignment.assignment_id,
                    order_id=existing_assignment.order_id,
                    executor_id=existing_assignment.executor_id,
                    status=existing_assignment.status,
                    confirmed_at=existing_assignment.confirmed_at or get_current_rfc3339(),
                )
            else:
                res = JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content=AssignmentError(
                        code="ORDER_ALREADY_ASSIGNED",
                        message=f"Order {payload.order_id} is already assigned to an executor",
                        retryable=False,
                    ).model_dump(),
                )

        future.set_result(res)
        return res
    except Exception as exc:
        if not future.done():
            future.set_exception(exc)
        raise
    finally:
        async with _assignment_lock:
            _in_flight_orders.pop(payload.order_id, None)
            _in_flight_assignments.pop(payload.assignment_id, None)
