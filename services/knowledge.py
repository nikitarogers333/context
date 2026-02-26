"""Knowledge entries router — CRUD + vector search for cross-project knowledge graph."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db as get_session
from models.chat import KnowledgeEntry
from services.auth import require_api_key
from services.embeddings import embed_texts
from services.schemas import KnowledgeCreate, KnowledgeOut, KnowledgeSearch

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=KnowledgeOut, status_code=201)
async def create_knowledge(req: KnowledgeCreate, db: AsyncSession = Depends(get_session)):
    embed_text = f"{req.subject}: {req.content}"
    embeddings = await embed_texts([embed_text])

    entry = KnowledgeEntry(
        category=req.category,
        subject=req.subject,
        content=req.content,
        source_conversation_id=req.source_conversation_id,
        confidence=req.confidence,
        embedding=embeddings[0],
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("", response_model=list[KnowledgeOut])
async def list_knowledge(
    category: str | None = None,
    subject: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    stmt = select(KnowledgeEntry).order_by(KnowledgeEntry.updated_at.desc()).limit(limit)
    if category:
        stmt = stmt.where(KnowledgeEntry.category == category)
    if subject:
        stmt = stmt.where(KnowledgeEntry.subject == subject)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{entry_id}", response_model=KnowledgeOut)
async def get_knowledge(entry_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Knowledge entry not found")
    return entry


@router.put("/{entry_id}", response_model=KnowledgeOut)
async def update_knowledge(entry_id: str, req: KnowledgeCreate, db: AsyncSession = Depends(get_session)):
    """Update an existing knowledge entry (upsert-style by ID)."""
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Knowledge entry not found")

    embed_text = f"{req.subject}: {req.content}"
    embeddings = await embed_texts([embed_text])

    entry.category = req.category
    entry.subject = req.subject
    entry.content = req.content
    entry.confidence = req.confidence
    entry.source_conversation_id = req.source_conversation_id
    entry.embedding = embeddings[0]

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}")
async def delete_knowledge(entry_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Knowledge entry not found")
    await db.delete(entry)
    await db.commit()
    return {"deleted": True}


@router.post("/search", response_model=list[KnowledgeOut])
async def search_knowledge(req: KnowledgeSearch, db: AsyncSession = Depends(get_session)):
    """Vector similarity search over knowledge entries."""
    if req.query:
        q_emb = (await embed_texts([req.query]))[0]
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.embedding.is_not(None))

        if req.category:
            stmt = stmt.where(KnowledgeEntry.category == req.category)

        stmt = stmt.order_by(KnowledgeEntry.embedding.op("<->")(q_emb)).limit(req.k)
    else:
        stmt = select(KnowledgeEntry).order_by(KnowledgeEntry.updated_at.desc()).limit(req.k)
        if req.category:
            stmt = stmt.where(KnowledgeEntry.category == req.category)

    result = await db.execute(stmt)
    return result.scalars().all()
