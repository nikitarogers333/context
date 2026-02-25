from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — Railway provides DATABASE_URL (postgres://...)
    # We also accept database_url for local dev
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/context"
    database_public_url: str | None = None  # Railway sets this too

    # Embeddings
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"

    # Auth (optional shared secret)
    atlas_api_key: str | None = None

    @property
    def async_database_url(self) -> str:
        """Return an asyncpg-compatible connection string."""
        url = self.database_url
        # Railway provides postgres:// or postgresql:// — convert to asyncpg
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Already has +asyncpg? leave it
        return url


settings = Settings()
