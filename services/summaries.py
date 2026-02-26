"""Weekly summaries router — store/generate periodic compressed summaries."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db as get_session
from models.chat import WeeklySummary
from services.auth import require_api_key
from services.embeddings import embed_texts
from services.schemas import WeeklySummaryCreate, WeeklySummaryOut, WeeklySummaryQuery

router = APIRouter(prefix="/weekly-summaries", tags=["weekly-summaries"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=WeeklySummaryOut, status_code=201)
async def create_weekly_summary(req: WeeklySummaryCreate, db: AsyncSession = Depends(get_session)):
    embeddings = await embed_texts([req.summary])
    ws = WeeklySummary(
        week_start=req.week_start,
        week_end=req.week_end,
        summary=req.summary,
        projects_active=",".join(req.projects_active or []),
        ideas_mentioned=",".join(req.ideas_mentioned or []),
        embedding=embeddings[0],
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws


@router.get("", response_model=list[WeeklySummaryOut])
async def list_weekly_summaries(limit: int = 50, db: AsyncSession = Depends(get_session)):
    stmt = select(WeeklySummary).order_by(WeeklySummary.week_start.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{summary_id}", response_model=WeeklySummaryOut)
async def get_weekly_summary(summary_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(WeeklySummary).where(WeeklySummary.id == summary_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(404, "Weekly summary not found")
    return ws


@router.post("/search", response_model=list[WeeklySummaryOut])
async def search_weekly_summaries(req: WeeklySummaryQuery, db: AsyncSession = Depends(get_session)):
    if req.query:
        q_emb = (await embed_texts([req.query]))[0]
        stmt = select(WeeklySummary).where(WeeklySummary.embedding.is_not(None))
        stmt = stmt.order_by(WeeklySummary.embedding.op("<->")(q_emb)).limit(req.k)
    else:
        stmt = select(WeeklySummary).order_by(WeeklySummary.week_start.desc()).limit(req.k)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/generate", response_model=WeeklySummaryOut)
async def generate_weekly_summary(
    days: int = 7,
    db: AsyncSession = Depends(get_session),
):
    """Naive generator that creates a placeholder weekly summary window.

    This is a scaffold for Layer 4. Later, the Brain (or a worker) should call
    Context search + summarize via an LLM, then POST /weekly-summaries.
    """
    now = datetime.now(timezone.utc)
    week_end = now
    week_start = now - timedelta(days=days)

    summary_text = f"Summary placeholder for {week_start.date()} → {week_end.date()} (not yet auto-generated)."
    embeddings = await embed_texts([summary_text])

    ws = WeeklySummary(
        week_start=week_start,
        week_end=week_end,
        summary=summary_text,
        projects_active=None,
        ideas_mentioned=None,
        embedding=embeddings[0],
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws
