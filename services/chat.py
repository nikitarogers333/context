import tiktoken
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.chat import Conversation, Message
from services.auth import require_api_key
from services.embeddings import embed_texts
from services.schemas import ConversationCreate, ConversationOut

router = APIRouter(dependencies=[Depends(require_api_key)])


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


@router.post("/", response_model=ConversationOut)
async def create_conversation(payload: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conv = Conversation(project=payload.project, title=payload.title)
    db.add(conv)
    await db.flush()

    contents = [m.content for m in payload.messages]
    embeddings = await embed_texts(contents)

    for m, e in zip(payload.messages, embeddings, strict=False):
        msg = Message(
            conversation_id=conv.id,
            role=m.role,
            content=m.content,
            embedding=e,
            token_count=count_tokens(m.content),
        )
        db.add(msg)

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


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    conv = (await db.execute(select(Conversation).where(Conversation.id == conversation_id))).scalar_one()
    msgs = (
        await db.execute(select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc()))
    ).scalars().all()
    return {
        "id": str(conv.id),
        "project": conv.project,
        "title": conv.title,
        "summary": conv.summary,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "token_count": m.token_count,
                "created_at": m.created_at,
            }
            for m in msgs
        ],
    }
