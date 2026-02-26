"""TaskOutcome model — per-task result tracking for continuous improvement."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from models.base import Base, generate_ulid


class TaskResult(str, PyEnum):
    success = "success"
    partial = "partial"
    failure = "failure"


class TaskOutcome(Base):
    __tablename__ = "task_outcomes"

    id = Column(String, primary_key=True, default=generate_ulid)
    project = Column(String, nullable=True, index=True)
    conversation_id = Column(String, nullable=True)
    task_description = Column(Text, nullable=False)
    result = Column(Enum(TaskResult, name="task_result", create_constraint=False), nullable=False)
    cause = Column(Text, nullable=True)              # what caused success/failure
    fix = Column(Text, nullable=True)                # how it was resolved (if failure/partial)
    recommendation = Column(Text, nullable=True)     # what to do next time
    linked_commit = Column(String, nullable=True)    # commit SHA or PR URL
    linked_repo = Column(String, nullable=True)      # repo name
    tags = Column(ARRAY(String), default=list)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
