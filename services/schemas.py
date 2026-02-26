import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ConversationCreate(BaseModel):
    project: str | None = None
    title: str | None = None
    messages: list[MessageIn]


class ConversationOut(BaseModel):
    id: uuid.UUID
    project: str | None
    title: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    query: str
    # If set, searches only that project. If None and include_general is True,
    # searches across BOTH project-tagged and general conversations.
    project: str | None = None
    include_general: bool = True
    k: int = 8


class ProjectReassignRequest(BaseModel):
    conversation_id: str
    project: str | None = None


class SearchHit(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    role: str
    content: str
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]


# --- Insights ---

class InsightCreate(BaseModel):
    type: str = Field(..., pattern="^(lesson|mistake|retrospective|playbook|idea)$")
    project: str | None = None
    title: str
    content: str
    tags: str | None = None
    source_conversation_id: str | None = None
    source_task_id: str | None = None


class InsightOut(BaseModel):
    id: uuid.UUID
    type: str
    project: str | None
    title: str
    content: str
    tags: str | None
    created_at: datetime
    updated_at: datetime


class InsightSearch(BaseModel):
    query: str
    project: str | None = None
    type: str | None = None
    include_global: bool = True
    k: int = 10


# --- Repo Events ---

class RepoEventCreate(BaseModel):
    event_type: str = Field(..., pattern="^(commit|pr|release|tag)$")
    repo: str
    project: str | None = None
    ref: str | None = None
    author: str | None = None
    title: str
    body: str | None = None
    diff_summary: str | None = None
    url: str | None = None
    event_at: datetime


class RepoEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    repo: str
    project: str | None
    ref: str | None
    author: str | None
    title: str
    body: str | None
    url: str | None
    event_at: datetime
    created_at: datetime


class RepoEventQuery(BaseModel):
    query: str | None = None
    repo: str | None = None
    project: str | None = None
    event_type: str | None = None
    k: int = 20


# --- Task Outcomes ---

class TaskOutcomeCreate(BaseModel):
    project: str | None = None
    result: str = Field(..., pattern="^(success|failure|partial)$")
    task_description: str
    cause: str | None = None
    fix: str | None = None
    recommendation: str | None = None
    linked_commit: str | None = None
    conversation_id: str | None = None
    tags: str | None = None


class TaskOutcomeOut(BaseModel):
    id: uuid.UUID
    project: str | None
    result: str
    task_description: str
    cause: str | None
    fix: str | None
    recommendation: str | None
    linked_commit: str | None
    tags: str | None
    created_at: datetime


class TaskOutcomeQuery(BaseModel):
    query: str | None = None
    project: str | None = None
    result: str | None = None
    k: int = 20
