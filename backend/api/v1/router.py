"""API v1 route aggregation."""

from fastapi import APIRouter

from backend.api.v1.auth import router as auth_router

router = APIRouter()

router.include_router(auth_router)


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Lightweight API availability check."""
    return {"status": "ok"}
