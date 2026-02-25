import os
from typing import Sequence

import numpy as np

from core.settings import settings


def _dim_for_model(model: str) -> int:
    # Default dims for OpenAI text-embedding-3-small/large; configurable later.
    if "large" in model:
        return 3072
    return 1536


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed texts using OpenAI if configured; otherwise return deterministic hash embeddings.

    The hash fallback keeps local/dev working without external keys.
    """
    if settings.openai_api_key:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.embeddings.create(model=settings.embedding_model, input=list(texts))
        return [d.embedding for d in resp.data]

    # Fallback: stable pseudo-embedding
    dim = _dim_for_model(settings.embedding_model)
    out: list[list[float]] = []
    for t in texts:
        seed = abs(hash(t)) % (2**32)
        rng = np.random.default_rng(seed)
        v = rng.normal(size=(dim,)).astype(np.float32)
        v /= np.linalg.norm(v) + 1e-8
        out.append(v.tolist())
    return out
