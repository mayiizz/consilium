from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/api/health")
async def api_health() -> dict:
    from app.core.config import get_settings

    settings = get_settings()
    return {
        "status": "ok",
        "service": "consilium-api",
        "groq_configured": bool(settings.groq_api_key),
    }
