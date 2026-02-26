"""Global summary generation over *all* messages (across all projects + general).

This endpoint is meant to answer: "Summarize our entire conversation history".
It works by pulling messages in a time window, summarizing in chunks (map step),
then merging those chunk summaries (reduce step) so it scales.

We store the result as a WeeklySummary row with projects_active/ideas_mentioned
(best-effort) so it can be retrieved later via /retrieve.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db as get_session
from models.chat import Conversation, Message, WeeklySummary
from services.auth import require_api_key
from services.embeddings import embed_texts
from services.llm import llm_summarize

router = APIRouter(prefix="/summaries", tags=["summaries"], dependencies=[Depends(require_api_key)])


class GlobalSummaryGenerateRequest(BaseModel):
    days: int = Field(90, ge=1, le=3650)
    max_messages: int = Field(8000, ge=100, le=50000)
    chunk_chars: int = Field(45000, ge=5000, le=120000)
    model: str = "gpt-4o-mini"


def _parse_header_list(text: str, header: str) -> list[str] | None:
    for line in text.splitlines():
        if line.lower().startswith(header.lower()):
            rest = line.split(":", 1)[1].strip()
            if not rest:
                return None
            return [x.strip() for x in rest.split(",") if x.strip()]
    return None


@router.post("/global/generate")
async def generate_global_summary(req: GlobalSummaryGenerateRequest, db: AsyncSession = Depends(get_session)):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=req.days)

    stmt = (
        select(
            Message.role,
            Message.content,
            Message.created_at,
            Conversation.project,
        )
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.created_at >= start)
        .order_by(Message.created_at.asc())
        .limit(req.max_messages)
    )

    rows = (await db.execute(stmt)).all()

    # Build a single transcript string, then chunk it by character count.
    lines = [
        f"[{r.created_at.isoformat()}] ({r.project or 'general'}) {r.role}: {r.content}"
        for r in rows
    ]
    transcript = "\n".join(lines)

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for line in lines:
        # +1 for newline
        l = len(line) + 1
        if buf and buf_len + l > req.chunk_chars:
            chunks.append("\n".join(buf))
            buf = []
            buf_len = 0
        buf.append(line)
        buf_len += l
    if buf:
        chunks.append("\n".join(buf))

    # Map step: summarize each chunk
    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        prompt = (
            "Summarize this slice of Atlas conversation history. Be concise and factual.\n\n"
            "Return bullets under these headings:\n"
            "- Key events/changes (3-8 bullets)\n"
            "- Decisions (0-6 bullets)\n"
            "- Mistakes / failure patterns (0-6 bullets)\n"
            "- Preferences (0-6 bullets)\n"
            "- Open threads / next steps (0-6 bullets)\n\n"
            f"Slice {i}/{len(chunks)} (time window starts {start.date()}):\n\n"
            f"Transcript:\n{chunk}"
        )
        chunk_summaries.append(await llm_summarize(prompt, model=req.model))

    # Reduce step: merge chunk summaries into one global summary
    reduce_prompt = (
        "Combine these partial summaries into ONE global summary of the full history window.\n"
        "De-duplicate aggressively and keep it short.\n\n"
        "Return in this exact format:\n"
        "Projects active: comma-separated list\n"
        "Themes: 3-8 bullets\n"
        "Key decisions: 3-10 bullets\n"
        "Recurring mistakes: 0-8 bullets\n"
        "Preferences & patterns: 3-10 bullets\n"
        "Current state: 3-8 bullets\n"
        "Next steps: 3-10 bullets\n"
        "Ideas mentioned: comma-separated list\n\n"
        f"Window: {start.date()} -> {now.date()}\n\n"
        "Partial summaries:\n" + "\n\n---\n\n".join(chunk_summaries)
    )

    summary_text = await llm_summarize(reduce_prompt, model=req.model)

    projects_active = _parse_header_list(summary_text, "Projects active")
    ideas_mentioned = _parse_header_list(summary_text, "Ideas mentioned")

    emb = (await embed_texts([summary_text]))[0]

    ws = WeeklySummary(
        week_start=start,
        week_end=now,
        summary=summary_text,
        projects_active=",".join(projects_active) if projects_active else None,
        ideas_mentioned=",".join(ideas_mentioned) if ideas_mentioned else None,
        embedding=emb,
    )

    db.add(ws)
    await db.commit()
    await db.refresh(ws)

    return {
        "id": str(ws.id),
        "window": {"start": ws.week_start.isoformat(), "end": ws.week_end.isoformat()},
        "summary": ws.summary,
        "projects_active": projects_active,
        "ideas_mentioned": ideas_mentioned,
        "messages_considered": len(rows),
        "chunks": len(chunks),
    }
