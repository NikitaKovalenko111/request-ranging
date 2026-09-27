import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field


def get_current_rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    event_version: int = 1
    occurred_at: str = Field(default_factory=get_current_rfc3339)
    source: str = "ais-simulator"
    payload: Dict[str, Any]


class OrderStatusChangedPayload(BaseModel):
    order_id: str
    previous_status: str
    status: str
    version: int
