import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.chat import Conversation
from services.auth import require_api_key
from services.schemas import ConversationOut, ProjectReassignRequest

router = APIRouter(prefix="/projects", dependencies=[Depends(require_api_key)])


@router.post("/reassign", response_model=ConversationOut)
async def reassign_conversation(payload: ProjectReassignRequest, db: AsyncSession = Depends(get_db)):
    """Move a conversation into/out of a project by updating its `project` field.

    Set project to null to make it a general conversation.
    """
    try:
        conv_id = uuid.UUID(payload.conversation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation_id")

    conv = (await db.execute(select(Conversation).where(Conversation.id == conv_id))).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.project = payload.project
    await db.commit()
    await db.refresh(conv)

    return ConversationOut(
        id=conv.id,
        project=conv.project,
        title=conv.title,
        summary=conv.summary,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )
