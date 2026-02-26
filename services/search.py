from fastapi import APIRouter, Depends
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.chat import Message
from services.auth import require_api_key
from services.embeddings import embed_texts
from services.schemas import SearchRequest, SearchResponse

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/messages", response_model=SearchResponse)
async def search_messages(payload: SearchRequest, db: AsyncSession = Depends(get_db)):
    q_emb = (await embed_texts([payload.query]))[0]

    stmt: Select = select(
        Message.id,
        Message.conversation_id,
        Message.role,
        Message.content,
        # pgvector distance: smaller is closer. We'll convert to a similarity-ish score.
        (1.0 / (1.0 + (Message.embedding.op("<->")(q_emb)))).label("score"),
    ).where(Message.embedding.is_not(None))

    # project lives on conversation; simplest v1 join
    from models.chat import Conversation

    if payload.project is not None:
        if payload.include_general:
            stmt = stmt.join(Conversation, Conversation.id == Message.conversation_id).where(
                (Conversation.project == payload.project) | (Conversation.project.is_(None))
            )
        else:
            stmt = stmt.join(Conversation, Conversation.id == Message.conversation_id).where(
                Conversation.project == payload.project
            )

    stmt = stmt.order_by(Message.embedding.op("<->")(q_emb)).limit(payload.k)

    rows = (await db.execute(stmt)).all()
    return SearchResponse(
        hits=[
            {
                "conversation_id": r.conversation_id,
                "message_id": r.id,
                "role": r.role,
                "content": r.content,
                "score": float(r.score),
            }
            for r in rows
        ]
    )
