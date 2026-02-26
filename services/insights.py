"""Insights router — CRUD + search for lessons, mistakes, retrospectives, playbooks, ideas."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.insight import Insight
from services.auth import require_api_key
from services.schemas import InsightCreate, InsightOut, InsightSearch

router = APIRouter(prefix="/insights", tags=["insights"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=InsightOut, status_code=201)
async def create_insight(req: InsightCreate, db: AsyncSession = Depends(get_session)):
    tags_list = [t.strip() for t in req.tags.split(",")] if req.tags else []
    insight = Insight(
        type=req.type,
        title=req.title,
        content=req.content,
        project=req.project,
        tags=tags_list,
        source_conversation_id=req.source_conversation_id,
        source_task_id=req.source_task_id,
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)
    return insight


@router.get("", response_model=list[InsightOut])
async def list_insights(
    project: str | None = None,
    type: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Insight).order_by(Insight.created_at.desc()).limit(limit)
    if project is not None:
        stmt = stmt.where(Insight.project == project)
    if type is not None:
        stmt = stmt.where(Insight.type == type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{insight_id}", response_model=InsightOut)
async def get_insight(insight_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Insight).where(Insight.id == insight_id))
    insight = result.scalar_one_or_none()
    if not insight:
        from fastapi import HTTPException
        raise HTTPException(404, "Insight not found")
    return insight


@router.post("/search", response_model=list[InsightOut])
async def search_insights(req: InsightSearch, db: AsyncSession = Depends(get_session)):
    """Search insights by text match on title/content, filtered by project/type."""
    stmt = select(Insight).order_by(Insight.created_at.desc()).limit(req.k)

    if req.project and req.include_global:
        stmt = stmt.where((Insight.project == req.project) | (Insight.project.is_(None)))
    elif req.project:
        stmt = stmt.where(Insight.project == req.project)
    # else: no project filter = search all

    if req.type:
        stmt = stmt.where(Insight.type == req.type)

    # Text search: simple ILIKE on title + content
    if req.query:
        pattern = f"%{req.query}%"
        stmt = stmt.where(
            Insight.title.ilike(pattern) | Insight.content.ilike(pattern)
        )

    result = await db.execute(stmt)
    return result.scalars().all()
