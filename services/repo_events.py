"""Repo events router — ingest + vector search for commits, PRs, releases from GitHub."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db as get_session
from models.repo_event import RepoEvent
from services.auth import require_api_key
from services.embeddings import embed_texts
from services.schemas import RepoEventCreate, RepoEventOut, RepoEventQuery

router = APIRouter(prefix="/repo-events", tags=["repo-events"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=RepoEventOut, status_code=201)
async def create_repo_event(req: RepoEventCreate, db: AsyncSession = Depends(get_session)):
    # Generate embedding from title + body
    embed_text = f"{req.title}\n{req.body or ''}"
    embeddings = await embed_texts([embed_text])

    event = RepoEvent(
        event_type=req.event_type,
        repo=req.repo,
        project=req.project,
        ref=req.ref,
        title=req.title,
        body=req.body,
        diff_summary=req.diff_summary,
        author=req.author,
        url=req.url,
        event_at=req.event_at,
        embedding=embeddings[0],
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.post("/webhook", status_code=201)
async def github_webhook(payload: dict, db: AsyncSession = Depends(get_session)):
    """Ingest a raw GitHub webhook payload (push, pull_request, release)."""
    events_created = []
    texts_to_embed = []
    event_objects = []

    # Push event → commits
    if "commits" in payload:
        repo = payload.get("repository", {}).get("full_name", "")
        for c in payload["commits"]:
            title = c.get("message", "").split("\n")[0]
            body = c.get("message", "")
            event = RepoEvent(
                event_type="commit",
                repo=repo,
                ref=payload.get("ref", ""),
                title=title,
                body=body,
                author=c.get("author", {}).get("username") or c.get("author", {}).get("name"),
                url=c.get("url", ""),
                event_at=c.get("timestamp", "2000-01-01T00:00:00Z"),
            )
            event_objects.append(event)
            texts_to_embed.append(f"{title}\n{body}")

    # Pull request event
    elif "pull_request" in payload:
        pr = payload["pull_request"]
        repo = payload.get("repository", {}).get("full_name", "")
        title = pr.get("title", "")
        body = pr.get("body", "") or ""
        event = RepoEvent(
            event_type="pr",
            repo=repo,
            ref=pr.get("head", {}).get("ref", ""),
            title=title,
            body=body,
            author=pr.get("user", {}).get("login", ""),
            url=pr.get("html_url", ""),
            event_at=pr.get("updated_at") or pr.get("created_at", "2000-01-01T00:00:00Z"),
        )
        event_objects.append(event)
        texts_to_embed.append(f"{title}\n{body}")

    # Release event
    elif "release" in payload:
        rel = payload["release"]
        repo = payload.get("repository", {}).get("full_name", "")
        title = rel.get("name", "") or rel.get("tag_name", "")
        body = rel.get("body", "") or ""
        event = RepoEvent(
            event_type="release",
            repo=repo,
            ref=rel.get("tag_name", ""),
            title=title,
            body=body,
            author=rel.get("author", {}).get("login", ""),
            url=rel.get("html_url", ""),
            event_at=rel.get("published_at") or rel.get("created_at", "2000-01-01T00:00:00Z"),
        )
        event_objects.append(event)
        texts_to_embed.append(f"{title}\n{body}")

    # Batch embed all events
    if event_objects and texts_to_embed:
        try:
            embeddings = await embed_texts(texts_to_embed)
            for evt, emb in zip(event_objects, embeddings):
                evt.embedding = emb
        except Exception:
            pass  # proceed without embeddings if embedding fails

        for evt in event_objects:
            db.add(evt)
        await db.commit()
        events_created = event_objects

    return {"ingested": len(events_created)}


@router.post("/search", response_model=list[RepoEventOut])
async def search_repo_events(req: RepoEventQuery, db: AsyncSession = Depends(get_session)):
    """Search repo events — vector similarity when query provided, otherwise filtered list."""
    if req.query:
        q_emb = (await embed_texts([req.query]))[0]
        stmt = select(RepoEvent).where(RepoEvent.embedding.is_not(None))

        if req.repo:
            stmt = stmt.where(RepoEvent.repo == req.repo)
        if req.project:
            stmt = stmt.where(RepoEvent.project == req.project)
        if req.event_type:
            stmt = stmt.where(RepoEvent.event_type == req.event_type)

        stmt = stmt.order_by(RepoEvent.embedding.op("<->")(q_emb)).limit(req.k)
    else:
        stmt = select(RepoEvent).order_by(RepoEvent.event_at.desc()).limit(req.k)
        if req.repo:
            stmt = stmt.where(RepoEvent.repo == req.repo)
        if req.project:
            stmt = stmt.where(RepoEvent.project == req.project)
        if req.event_type:
            stmt = stmt.where(RepoEvent.event_type == req.event_type)

    result = await db.execute(stmt)
    return result.scalars().all()
