"""Insight model — lessons learned, mistake patterns, retrospectives, playbooks, ideas."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY

from models.base import Base, generate_ulid


class InsightType(str, PyEnum):
    lesson = "lesson"
    mistake = "mistake"
    retrospective = "retrospective"
    playbook = "playbook"
    idea = "idea"


class Insight(Base):
    __tablename__ = "insights"

    id = Column(String, primary_key=True, default=generate_ulid)
    type = Column(Enum(InsightType, name="insight_type", create_constraint=False), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    project = Column(String, nullable=True, index=True)  # null = global
    tags = Column(ARRAY(String), default=list)
    source_conversation_id = Column(String, nullable=True)
    source_task_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
