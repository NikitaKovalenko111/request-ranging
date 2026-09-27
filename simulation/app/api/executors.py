from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.executor import Executor, ExecutorCreate, ExecutorPatch
from ..storage.database import get_db_session
from ..storage.repository import ExecutorRepository
from ..kafka.producer import kafka_producer

router = APIRouter(prefix="/api/v1/executors", tags=["Executors"])


@router.post("", response_model=Executor, status_code=status.HTTP_201_CREATED)
async def create_executor(
    payload: ExecutorCreate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = ExecutorRepository(session)
    existing = await repo.get_by_id(payload.executor_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EXECUTOR_ALREADY_EXISTS", "message": f"Executor {payload.executor_id} already exists", "retryable": False},
        )

    row = await repo.create(
        executor_id=payload.executor_id,
        active=payload.active,
        capacity=payload.capacity,
        daily_limit=payload.daily_limit,
        skills=payload.skills or [],
        attributes=payload.attributes or {},
        version=1,
    )
    exec_dict = row.to_dict()
    await kafka_producer.publish_executor_created(exec_dict)
    return Executor(**exec_dict)


@router.get("", response_model=List[Executor])
async def list_executors(
    active: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
):
    repo = ExecutorRepository(session)
    rows = await repo.list_executors(active=active, limit=limit, offset=offset)
    return [Executor(**r.to_dict()) for r in rows]


@router.get("/{executor_id}", response_model=Executor)
async def get_executor(
    executor_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    repo = ExecutorRepository(session)
    row = await repo.get_by_id(executor_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXECUTOR_NOT_FOUND", "message": f"Executor {executor_id} not found", "retryable": False},
        )
    return Executor(**row.to_dict())


@router.patch("/{executor_id}", response_model=Executor)
async def patch_executor(
    executor_id: str,
    payload: ExecutorPatch,
    session: AsyncSession = Depends(get_db_session),
):
    repo = ExecutorRepository(session)
    row = await repo.update_executor(
        executor_id=executor_id,
        active=payload.active,
        capacity=payload.capacity,
        daily_limit=payload.daily_limit,
        skills=payload.skills,
        attributes=payload.attributes,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXECUTOR_NOT_FOUND", "message": f"Executor {executor_id} not found", "retryable": False},
        )

    exec_dict = row.to_dict()
    await kafka_producer.publish_executor_updated(exec_dict)
    return Executor(**exec_dict)
