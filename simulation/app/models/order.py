from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class OrderStatus(str, Enum):
    PROCESSED = "processed"
    AWAIT = "await"
    ACCEPT = "accept"
    REJECT = "reject"


class OrderAttributes(BaseModel):
    model_config = ConfigDict(extra="allow")

    sum: int
    order_type: str
    subject: str
    vip: bool = False
    client_msp: Optional[str] = None
    executor_msp: Optional[str] = None
    text: Optional[str] = None
    region: Optional[str] = None


class OrderBase(BaseModel):
    parent_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PROCESSED
    weight: float = Field(gt=0, default=1.0)
    attributes: OrderAttributes


class OrderCreate(BaseModel):
    order_id: Optional[str] = None
    parent_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PROCESSED
    weight: float = Field(gt=0, default=1.0)
    attributes: OrderAttributes


class OrderPatch(BaseModel):
    status: Optional[OrderStatus] = None
    weight: Optional[float] = Field(default=None, gt=0)
    attributes: Optional[Dict[str, Any]] = None


class Order(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    parent_id: Optional[str] = None
    status: str
    weight: float
    version: int
    attributes: Dict[str, Any]
    assigned_executor_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
