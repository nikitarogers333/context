from fastapi import Header, HTTPException

from core.settings import settings


async def require_api_key(x_atlas_api_key: str | None = Header(default=None)):
    """Simple shared-secret auth.

    - If settings.atlas_api_key is unset, auth is disabled.
    - Otherwise require X-Atlas-Api-Key header.
    """
    if not settings.atlas_api_key:
        return
    if x_atlas_api_key != settings.atlas_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
