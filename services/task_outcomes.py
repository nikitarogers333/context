"""Task outcomes router — track task results with vector search for continuous improvement."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db as get_session
from models.task_outcome import TaskOutcome
from services.auth import require_api_key
from services.embeddings import embed_texts
from services.schemas import TaskOutcomeCreate, TaskOutcomeOut, TaskOutcomeQuery

router = APIRouter(prefix="/task-outcomes", tags=["task-outcomes"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=TaskOutcomeOut, status_code=201)
async def create_task_outcome(req: TaskOutcomeCreate, db: AsyncSession = Depends(get_session)):
    tags_list = [t.strip() for t in req.tags.split(",")] if req.tags else []

    # Generate embedding from task description + cause + recommendation
    embed_text = req.task_description
    if req.cause:
        embed_text += f"\nCause: {req.cause}"
    if req.fix:
        embed_text += f"\nFix: {req.fix}"
    if req.recommendation:
        embed_text += f"\nRecommendation: {req.recommendation}"
    embeddings = await embed_texts([embed_text])

    outcome = TaskOutcome(
        project=req.project,
        conversation_id=req.conversation_id,
        task_description=req.task_description,
        result=req.result,
        cause=req.cause,
        fix=req.fix,
        recommendation=req.recommendation,
        linked_commit=req.linked_commit,
        tags=tags_list,
        embedding=embeddings[0],
    )
    db.add(outcome)
    await db.commit()
    await db.refresh(outcome)
    return outcome


@router.post("/search", response_model=list[TaskOutcomeOut])
async def search_task_outcomes(req: TaskOutcomeQuery, db: AsyncSession = Depends(get_session)):
    """Search task outcomes — vector similarity when query provided."""
    if req.query:
        q_emb = (await embed_texts([req.query]))[0]
        stmt = select(TaskOutcome).where(TaskOutcome.embedding.is_not(None))

        if req.project:
            stmt = stmt.where(TaskOutcome.project == req.project)
        if req.result:
            stmt = stmt.where(TaskOutcome.result == req.result)

        stmt = stmt.order_by(TaskOutcome.embedding.op("<->")(q_emb)).limit(req.k)
    else:
        stmt = select(TaskOutcome).order_by(TaskOutcome.created_at.desc()).limit(req.k)
        if req.project:
            stmt = stmt.where(TaskOutcome.project == req.project)
        if req.result:
            stmt = stmt.where(TaskOutcome.result == req.result)

    result = await db.execute(stmt)
    return result.scalars().all()
