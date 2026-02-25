# Context

A standalone, deployable **layered memory** service for Atlas — store everything, retrieve what matters.

- **Layer 1**: Chat archival (conversations + messages → Postgres)
- **Layer 2**: Vector embeddings via `pgvector` for semantic search
- **Layer 3**: Cross-project knowledge extraction (preferences, patterns, entities)
- **Layer 4**: Periodic summaries (weekly/monthly compressed digests)

## Architecture

```
iPhone (PWA) → Atlas Gateway → Context Service
                                  ├── Chat Archive (Postgres)
                                  ├── Vector Search (pgvector)
                                  ├── Knowledge Graph (entities + relations)
                                  └── Summary Engine (periodic digests)
```

## Quickstart (local)

### 1) Postgres + pgvector

You need Postgres with the `vector` extension enabled.

### 2) Environment

Create `.env`:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/context
ATLAS_API_KEY=dev-secret
OPENAI_API_KEY=...        # optional; uses deterministic hash embeddings without
EMBEDDING_MODEL=text-embedding-3-small
```

### 3) Run

```
pip install -e .
uvicorn api.main:app --reload --port 8090
```

### 4) Endpoints

- `POST /chats/` — archive a conversation with messages (auto-embeds each message)
- `POST /search/messages` — semantic search over all messages
- `GET /health` — service health check

## Deployment

Target: **Railway** (persistent API + managed Postgres + pgvector + background workers)

## Roadmap

- [ ] Chunking strategy for long messages
- [ ] Conversation-level summary embeddings
- [ ] Knowledge extraction jobs (preferences, entities, patterns)
- [ ] Weekly/monthly auto-summaries
- [ ] Multi-user scoping
- [ ] Integration with Atlas brain (auto-archive every conversation)
