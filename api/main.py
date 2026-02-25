from fastapi import FastAPI

from services.health import router as health_router
from services.chat import router as chat_router
from services.search import router as search_router

app = FastAPI(title="Context API", version="0.1.0")

@app.on_event("startup")
async def _startup() -> None:
    # Ensure pgvector extension + tables exist
    from core.database import init_db

    await init_db()


app.include_router(health_router, prefix="/health")
app.include_router(chat_router, prefix="/chats")
app.include_router(search_router, prefix="/search")
