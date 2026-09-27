from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ExecutorAttributes(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_accept_sum: Optional[int] = None
    max_accept_sum: Optional[int] = None
    client_msp: Optional[List[str]] = None
    executor_msp: Optional[List[str]] = None
    order_types: Optional[List[str]] = None
    subjects: Optional[List[str]] = None
    vip_allowed: Optional[bool] = None
    regions: Optional[List[str]] = None


class ExecutorCreate(BaseModel):
    executor_id: str
    active: bool = True
    capacity: float = Field(gt=0, default=1.0)
    daily_limit: Optional[int] = None
    skills: Optional[List[str]] = Field(default_factory=list)
    attributes: Optional[Dict[str, Any]] = None


class ExecutorPatch(BaseModel):
    active: Optional[bool] = None
    capacity: Optional[float] = Field(default=None, gt=0)
    daily_limit: Optional[int] = None
    skills: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None


class Executor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    executor_id: str
    active: bool
    capacity: float
    daily_limit: Optional[int] = None
    version: int
    skills: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
