# atlas-memory

A standalone, deployable **layered memory** service for Atlas:

- Chat archival (conversations + messages)
- Embeddings stored in Postgres via `pgvector`
- Semantic search (retrieve top-k relevant messages)
- Foundation for cross-project knowledge extraction + weekly/monthly summaries

## Quickstart (local)

### 1) Postgres + pgvector

You need Postgres with the `vector` extension available.

### 2) Environment

Create `.env`:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/atlas_memory
ATLAS_API_KEY=dev-secret  # optional
OPENAI_API_KEY=...        # optional; otherwise uses deterministic hash embeddings
EMBEDDING_MODEL=text-embedding-3-small
```

### 3) Run

```
pip install -e .
uvicorn api.main:app --reload --port 8090
```

### 4) Endpoints

- `POST /chats/` create a conversation with messages (embeds each message)
- `POST /search/messages` semantic search over messages

## Next steps

- Chunking strategy for long messages
- Conversation-level summary + summary embedding
- Knowledge extraction jobs (preferences, entities, patterns)
- Multi-tenant/user scoping and stronger auth
