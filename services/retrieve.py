"""Unified retrieval endpoint — searches messages, insights, knowledge, task outcomes, summaries in one call.

This is the single endpoint Atlas's brain calls before every task to get relevant context.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db as get_session
from models.chat import Conversation, Message, KnowledgeEntry, WeeklySummary
from models.insight import Insight
from models.task_outcome import TaskOutcome
from services.auth import require_api_key
from services.embeddings import embed_texts

router = APIRouter(prefix="/retrieve", tags=["retrieve"], dependencies=[Depends(require_api_key)])


class RetrieveRequest(BaseModel):
    query: str
    project: str | None = None
    include_general: bool = True
    k_messages: int = 5
    k_insights: int = 3
    k_knowledge: int = 3
    k_outcomes: int = 3
    k_summaries: int = 2


class RetrieveResponse(BaseModel):
    messages: list[dict]
    insights: list[dict]
    knowledge: list[dict]
    task_outcomes: list[dict]
    summaries: list[dict]


@router.post("", response_model=RetrieveResponse)
async def retrieve(req: RetrieveRequest, db: AsyncSession = Depends(get_session)):
    """Single-call retrieval across all Context layers. Returns the most relevant
    items from each table, ranked by vector similarity to the query."""

    q_emb = (await embed_texts([req.query]))[0]

    # --- Messages ---
    msg_stmt = select(
        Message.id, Message.conversation_id, Message.role, Message.content,
        (1.0 / (1.0 + Message.embedding.op("<->")(q_emb))).label("score"),
    ).where(Message.embedding.is_not(None))

    if req.project is not None:
        if req.include_general:
            msg_stmt = msg_stmt.join(Conversation, Conversation.id == Message.conversation_id).where(
                (Conversation.project == req.project) | (Conversation.project.is_(None))
            )
        else:
            msg_stmt = msg_stmt.join(Conversation, Conversation.id == Message.conversation_id).where(
                Conversation.project == req.project
            )

    msg_stmt = msg_stmt.order_by(Message.embedding.op("<->")(q_emb)).limit(req.k_messages)
    msg_rows = (await db.execute(msg_stmt)).all()
    messages = [
        {"conversation_id": str(r.conversation_id), "role": r.role, "content": r.content, "score": float(r.score)}
        for r in msg_rows
    ]

    # --- Insights ---
    ins_stmt = select(Insight).where(Insight.embedding.is_not(None))
    if req.project:
        if req.include_general:
            ins_stmt = ins_stmt.where((Insight.project == req.project) | (Insight.project.is_(None)))
        else:
            ins_stmt = ins_stmt.where(Insight.project == req.project)
    ins_stmt = ins_stmt.order_by(Insight.embedding.op("<->")(q_emb)).limit(req.k_insights)
    ins_rows = (await db.execute(ins_stmt)).scalars().all()
    insights = [
        {"type": i.type, "title": i.title, "content": i.content, "project": i.project}
        for i in ins_rows
    ]

    # --- Knowledge ---
    kn_stmt = select(KnowledgeEntry).where(KnowledgeEntry.embedding.is_not(None))
    kn_stmt = kn_stmt.order_by(KnowledgeEntry.embedding.op("<->")(q_emb)).limit(req.k_knowledge)
    kn_rows = (await db.execute(kn_stmt)).scalars().all()
    knowledge = [
        {"category": k.category, "subject": k.subject, "content": k.content, "confidence": k.confidence}
        for k in kn_rows
    ]

    # --- Task Outcomes ---
    to_stmt = select(TaskOutcome).where(TaskOutcome.embedding.is_not(None))
    if req.project:
        if req.include_general:
            to_stmt = to_stmt.where((TaskOutcome.project == req.project) | (TaskOutcome.project.is_(None)))
        else:
            to_stmt = to_stmt.where(TaskOutcome.project == req.project)
    to_stmt = to_stmt.order_by(TaskOutcome.embedding.op("<->")(q_emb)).limit(req.k_outcomes)
    to_rows = (await db.execute(to_stmt)).scalars().all()
    task_outcomes = [
        {"result": t.result, "task_description": t.task_description, "cause": t.cause,
         "fix": t.fix, "recommendation": t.recommendation}
        for t in to_rows
    ]

    # --- Weekly Summaries ---
    ws_stmt = select(WeeklySummary).where(WeeklySummary.embedding.is_not(None))
    ws_stmt = ws_stmt.order_by(WeeklySummary.embedding.op("<->")(q_emb)).limit(req.k_summaries)
    ws_rows = (await db.execute(ws_stmt)).scalars().all()
    summaries = [
        {"week_start": str(s.week_start), "week_end": str(s.week_end), "summary": s.summary}
        for s in ws_rows
    ]

    return RetrieveResponse(
        messages=messages,
        insights=insights,
        knowledge=knowledge,
        task_outcomes=task_outcomes,
        summaries=summaries,
    )
