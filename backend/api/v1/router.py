"""API v1 route aggregation."""

from fastapi import APIRouter

from backend.api.v1.activity import router as activity_router
from backend.api.v1.ai import router as ai_router
from backend.api.v1.attachments import router as attachments_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.comments import router as comments_router
from backend.api.v1.due_reminders import router as due_reminders_router
from backend.api.v1.notifications import router as notifications_router
from backend.api.v1.preferences import router as preferences_router
from backend.api.v1.projects import router as projects_router
from backend.api.v1.search import router as search_router
from backend.api.v1.tasks import router as tasks_router
from backend.api.v1.workspaces import router as workspaces_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(workspaces_router)
router.include_router(projects_router)
router.include_router(tasks_router)
router.include_router(comments_router)
router.include_router(notifications_router)
router.include_router(attachments_router)
router.include_router(search_router)
router.include_router(activity_router)
router.include_router(preferences_router)
router.include_router(ai_router)
router.include_router(due_reminders_router)


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Lightweight API availability check."""
    return {"status": "ok"}
