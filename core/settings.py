from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    # - Railway provides DATABASE_URL (usually postgres://...)
    # - Local dev can use DATABASE_URL or database_url
    #
    # IMPORTANT: pydantic-settings maps env vars by field name. Our field is
    # `database_url`, so by default it reads `DATABASE_URL` only if we add an alias.
    # Without this alias, Railway deployments won't see the injected DATABASE_URL.
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/context",
        validation_alias="DATABASE_URL",
    )
    database_public_url: str | None = None  # Railway may set this too

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
