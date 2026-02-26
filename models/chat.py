"""All SQLAlchemy models for the memory system."""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    summary_embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1536), nullable=True)
    token_count: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_embedding", "embedding", postgresql_using="ivfflat"),
    )


class KnowledgeEntry(Base):
    """Cross-project knowledge graph entries — preferences, patterns, entities."""
    __tablename__ = "knowledge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(50), index=True)  # preference | pattern | entity | insight
    subject: Mapped[str] = mapped_column(String(255), index=True)  # e.g. "ui_style", "deploy_platform"
    content: Mapped[str] = mapped_column(Text)  # e.g. "Prefers minimal UI with dark mode"
    embedding = mapped_column(Vector(1536), nullable=True)
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    confidence: Mapped[float] = mapped_column(default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WeeklySummary(Base):
    """Periodic compressed summaries of activity."""
    __tablename__ = "weekly_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    week_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str] = mapped_column(Text)
    projects_active: Mapped[str | None] = mapped_column(Text)  # comma-separated
    ideas_mentioned: Mapped[str | None] = mapped_column(Text)
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Insight(Base):
    """Derived lessons, mistakes, retrospectives, playbooks."""
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # lesson | mistake | retrospective | playbook | idea
    type: Mapped[str] = mapped_column(String(50), index=True)
    project: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)  # comma-separated
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RepoEvent(Base):
    """GitHub repo events: commits, PRs, releases."""
    __tablename__ = "repo_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # commit | pr | release | tag
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    repo: Mapped[str] = mapped_column(String(255), index=True)  # owner/repo
    project: Mapped[str | None] = mapped_column(String(255), index=True)
    ref: Mapped[str | None] = mapped_column(String(255))  # sha, PR number, tag name
    author: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)  # commit message body, PR body
    diff_summary: Mapped[str | None] = mapped_column(Text)  # optional summarized diff
    url: Mapped[str | None] = mapped_column(String(500))  # link to GitHub
    embedding = mapped_column(Vector(1536), nullable=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskOutcome(Base):
    """Per-task result tracking: what Atlas did, whether it worked, and what was learned."""
    __tablename__ = "task_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project: Mapped[str | None] = mapped_column(String(255), index=True)
    # success | failure | partial
    result: Mapped[str] = mapped_column(String(20), index=True)
    task_description: Mapped[str] = mapped_column(Text)
    cause: Mapped[str | None] = mapped_column(Text)  # what caused failure/success
    fix: Mapped[str | None] = mapped_column(Text)  # what fixed it (if failure)
    recommendation: Mapped[str | None] = mapped_column(Text)  # what to do next time
    linked_commit: Mapped[str | None] = mapped_column(String(255))  # sha or PR URL
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    tags: Mapped[str | None] = mapped_column(Text)  # comma-separated
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
