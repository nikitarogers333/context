"""Auto-extraction of structured memory from a conversation.

Called after chat ingest. Best-effort: failures should never break ingestion.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import Conversation, KnowledgeEntry
from models.insight import Insight
from models.task_outcome import TaskOutcome
from services.embeddings import embed_texts
from services.llm import llm_summarize


AUTO_EXTRACT_SYSTEM_PROMPT = """
Extract structured memory items from the conversation.

Return STRICT JSON with shape:
{
  "insights": [{"type":"lesson|mistake|retrospective|playbook|idea","title":"...","content":"...","tags":["..."]}],
  "knowledge": [{"category":"preference|pattern|entity|insight","subject":"...","content":"...","confidence":0.0}],
  "task_outcomes": [{"result":"success|partial|failure","task_description":"...","cause":null|"...","fix":null|"...","recommendation":null|"...","tags":["..."]}]
}

Rules:
- 0 to 5 items per list.
- Only include high-signal items that will matter later.
- Use short titles; content can be 1-4 sentences.
""".strip()


def _safe_list(x: Any) -> list:
    return x if isinstance(x, list) else []


async def auto_extract_from_conversation(
    *,
    db: AsyncSession,
    conversation: Conversation,
    messages: list[dict],
) -> dict:
    # Build compact transcript
    transcript_lines = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        transcript_lines.append(f"{role}: {content}")

    if not transcript_lines:
        return {"created": 0}

    prompt = (
        f"{AUTO_EXTRACT_SYSTEM_PROMPT}\n\n"
        f"Project: {conversation.project or 'general'}\n"
        f"Conversation ID: {conversation.id}\n\n"
        f"Transcript:\n" + "\n".join(transcript_lines[-60:])
    )

    text = await llm_summarize(prompt)

    try:
        data = json.loads(text)
    except Exception:
        # If model didn't return JSON, bail silently
        return {"created": 0, "error": "invalid_json"}

    created = 0

    # Insights
    for item in _safe_list(data.get("insights"))[:5]:
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        if not title or not content:
            continue
        emb = (await embed_texts([f"{title}\n{content}"]))[0]
        ins = Insight(
            type=item.get("type") or "lesson",
            project=conversation.project,
            title=title,
            content=content,
            tags=",".join(_safe_list(item.get("tags"))) or None,
            source_conversation_id=conversation.id,
            embedding=emb,
        )
        db.add(ins)
        created += 1

    # Knowledge
    for item in _safe_list(data.get("knowledge"))[:5]:
        subject = (item.get("subject") or "").strip()
        content = (item.get("content") or "").strip()
        if not subject or not content:
            continue
        emb = (await embed_texts([f"{subject}\n{content}"]))[0]
        kn = KnowledgeEntry(
            category=item.get("category") or "insight",
            subject=subject,
            content=content,
            confidence=float(item.get("confidence") or 1.0),
            source_conversation_id=conversation.id,
            embedding=emb,
        )
        db.add(kn)
        created += 1

    # Task outcomes
    for item in _safe_list(data.get("task_outcomes"))[:5]:
        task_description = (item.get("task_description") or "").strip()
        if not task_description:
            continue
        result = item.get("result") or "success"
        cause = item.get("cause")
        fix = item.get("fix")
        recommendation = item.get("recommendation")
        emb = (await embed_texts([task_description]))[0]
        to = TaskOutcome(
            project=conversation.project,
            result=result,
            task_description=task_description,
            cause=cause,
            fix=fix,
            recommendation=recommendation,
            conversation_id=conversation.id,
            tags=",".join(_safe_list(item.get("tags"))) or None,
            embedding=emb,
        )
        db.add(to)
        created += 1

    return {"created": created}
