import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.health import router as health_router
from services.chat import router as chat_router
from services.search import router as search_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try to init DB on startup; don't crash if DB not ready yet
    try:
        from core.database import init_db
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"DB init deferred (will retry on first request): {e}")
    yield


app = FastAPI(title="Context API", version="0.1.0", lifespan=lifespan)

app.include_router(health_router, prefix="/health")
app.include_router(chat_router, prefix="/chats")
app.include_router(search_router, prefix="/search")
