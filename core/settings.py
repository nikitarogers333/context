from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/atlas_memory"

    # Embeddings
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"

    # Auth (optional) - shared secret between gateway and this service
    atlas_api_key: str | None = None


settings = Settings()
