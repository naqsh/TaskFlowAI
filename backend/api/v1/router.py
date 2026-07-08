"""API v1 route aggregation."""

from fastapi import APIRouter

from backend.api.v1.auth import router as auth_router
from backend.api.v1.comments import router as comments_router
from backend.api.v1.projects import router as projects_router
from backend.api.v1.tasks import router as tasks_router
from backend.api.v1.workspaces import router as workspaces_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(workspaces_router)
router.include_router(projects_router)
router.include_router(tasks_router)
router.include_router(comments_router)


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Lightweight API availability check."""
    return {"status": "ok"}
