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
    project: str | None = None
    k: int = 8


class SearchHit(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    role: str
    content: str
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]
