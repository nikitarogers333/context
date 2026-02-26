"""RepoEvent model — commits, PRs, releases ingested from GitHub."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base, generate_ulid


class RepoEventType(str, PyEnum):
    commit = "commit"
    pr = "pr"
    release = "release"
    tag = "tag"


class RepoEvent(Base):
    __tablename__ = "repo_events"

    id = Column(String, primary_key=True, default=generate_ulid)
    event_type = Column(Enum(RepoEventType, name="repo_event_type", create_constraint=False), nullable=False)
    repo = Column(String, nullable=False, index=True)        # e.g. "nikitarogers333/context"
    project = Column(String, nullable=True, index=True)       # linked project name
    ref = Column(String, nullable=True)                        # branch, tag, sha
    title = Column(String, nullable=False)                     # commit msg first line / PR title / release name
    body = Column(Text, nullable=True)                         # full commit msg / PR body / release notes
    diff_summary = Column(Text, nullable=True)                 # summarized diff (optional)
    author = Column(String, nullable=True)
    url = Column(String, nullable=True)                        # GitHub URL
    metadata_ = Column("metadata", JSONB, default=dict)        # extra (files changed, labels, etc.)
    event_at = Column(DateTime, nullable=False)                # when the event happened on GitHub
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
