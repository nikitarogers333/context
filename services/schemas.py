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


# --- Knowledge ---

class KnowledgeCreate(BaseModel):
    category: str = Field(..., pattern="^(preference|pattern|entity|insight)$")
    subject: str
    content: str
    confidence: float = 1.0
    source_conversation_id: str | None = None


class KnowledgeOut(BaseModel):
    id: uuid.UUID
    category: str
    subject: str
    content: str
    confidence: float
    source_conversation_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeSearch(BaseModel):
    query: str | None = None
    category: str | None = None
    k: int = 10


# --- Weekly Summaries ---

class WeeklySummaryCreate(BaseModel):
    week_start: datetime
    week_end: datetime
    summary: str
    projects_active: list[str] | None = None
    ideas_mentioned: list[str] | None = None


class WeeklySummaryOut(BaseModel):
    id: uuid.UUID
    week_start: datetime
    week_end: datetime
    summary: str
    projects_active: str | None
    ideas_mentioned: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class WeeklySummaryQuery(BaseModel):
    query: str | None = None
    k: int = 10


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
    id: str
    type: str
    project: str | None
    title: str
    content: str
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InsightSearch(BaseModel):
    query: str | None = None
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
    id: str
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

    class Config:
        from_attributes = True


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
    id: str
    project: str | None
    result: str
    task_description: str
    cause: str | None
    fix: str | None
    recommendation: str | None
    linked_commit: str | None
    tags: list[str] | None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskOutcomeQuery(BaseModel):
    query: str | None = None
    project: str | None = None
    result: str | None = None
    k: int = 20
