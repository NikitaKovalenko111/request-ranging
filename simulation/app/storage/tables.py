import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, Index
from .database import Base


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class OrderRow(Base):
    __tablename__ = "orders"

    order_id = Column(String(64), primary_key=True, index=True)
    parent_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="processed", index=True)
    weight = Column(Float, nullable=False, default=1.0)
    version = Column(Integer, nullable=False, default=1)
    attributes_json = Column(Text, nullable=False, default="{}")
    assigned_executor_id = Column(String(64), nullable=True, index=True)
    created_at = Column(String(32), default=now_iso)
    updated_at = Column(String(32), default=now_iso, onupdate=now_iso)

    __table_args__ = (
        Index("ix_orders_status_assigned", "status", "assigned_executor_id"),
    )

    def to_dict(self):
        try:
            attrs = json.loads(self.attributes_json)
        except Exception:
            attrs = {}
        return {
            "order_id": self.order_id,
            "parent_id": self.parent_id,
            "status": self.status,
            "weight": self.weight,
            "version": self.version,
            "attributes": attrs,
            "assigned_executor_id": self.assigned_executor_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ExecutorRow(Base):
    __tablename__ = "executors"

    executor_id = Column(String(64), primary_key=True, index=True)
    active = Column(Boolean, nullable=False, default=True, index=True)
    capacity = Column(Float, nullable=False, default=1.0)
    daily_limit = Column(Integer, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    skills_json = Column(Text, nullable=False, default="[]")
    attributes_json = Column(Text, nullable=False, default="{}")
    created_at = Column(String(32), default=now_iso)
    updated_at = Column(String(32), default=now_iso, onupdate=now_iso)

    def to_dict(self):
        try:
            attrs = json.loads(self.attributes_json)
        except Exception:
            attrs = {}
        try:
            skills = json.loads(self.skills_json)
        except Exception:
            skills = []
        return {
            "executor_id": self.executor_id,
            "active": self.active,
            "capacity": self.capacity,
            "daily_limit": self.daily_limit,
            "version": self.version,
            "skills": skills,
            "attributes": attrs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AssignmentRow(Base):
    __tablename__ = "assignments"

    assignment_id = Column(String(64), primary_key=True, index=True)
    order_id = Column(String(64), nullable=False, unique=True, index=True)
    executor_id = Column(String(64), nullable=False, index=True)
    decided_at = Column(String(32), nullable=False)
    confirmed_at = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="confirmed")

    def to_dict(self):
        return {
            "assignment_id": self.assignment_id,
            "order_id": self.order_id,
            "executor_id": self.executor_id,
            "decided_at": self.decided_at,
            "confirmed_at": self.confirmed_at,
            "status": self.status,
        }
