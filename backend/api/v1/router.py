"""API v1 route aggregation."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Lightweight API availability check."""
    return {"status": "ok"}
