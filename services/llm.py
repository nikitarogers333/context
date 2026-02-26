"""Small helper for LLM calls (used for weekly summary generation and insight extraction).

We keep this separate so the rest of the service doesn't need to import OpenAI
unless it's actually used.
"""

from __future__ import annotations

from core.settings import settings


async def llm_summarize(prompt: str, *, model: str = "gpt-4o-mini") -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM summarization")

    try:
        from openai import AsyncOpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("OPENAI_API_KEY is set but the 'openai' package is not installed") from e

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Minimal, stable interface: use chat.completions.
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a concise assistant that produces structured outputs."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return (resp.choices[0].message.content or "").strip()
