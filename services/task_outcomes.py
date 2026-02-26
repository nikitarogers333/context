"""Task outcomes router — track task results for continuous improvement."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.task_outcome import TaskOutcome
from services.auth import verify_api_key
from services.schemas import TaskOutcomeCreate, TaskOutcomeOut, TaskOutcomeQuery

router = APIRouter(prefix="/task-outcomes", tags=["task-outcomes"], dependencies=[Depends(verify_api_key)])


@router.post("", response_model=TaskOutcomeOut, status_code=201)
async def create_task_outcome(req: TaskOutcomeCreate, db: AsyncSession = Depends(get_session)):
    tags_list = [t.strip() for t in req.tags.split(",")] if req.tags else []
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
    )
    db.add(outcome)
    await db.commit()
    await db.refresh(outcome)
    return outcome


@router.post("/search", response_model=list[TaskOutcomeOut])
async def search_task_outcomes(req: TaskOutcomeQuery, db: AsyncSession = Depends(get_session)):
    stmt = select(TaskOutcome).order_by(TaskOutcome.created_at.desc()).limit(req.k)
    if req.project:
        stmt = stmt.where(TaskOutcome.project == req.project)
    if req.result:
        stmt = stmt.where(TaskOutcome.result == req.result)
    if req.query:
        pattern = f"%{req.query}%"
        stmt = stmt.where(
            TaskOutcome.task_description.ilike(pattern) | TaskOutcome.cause.ilike(pattern)
        )
    result = await db.execute(stmt)
    return result.scalars().all()
