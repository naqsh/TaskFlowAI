"""Attachment handling (TF-014).

MVP storage: local filesystem bytes + DB metadata.
Signed download tokens are HMAC-based and time-bounded.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import mimetypes
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Attachment
from backend.dependencies.rbac import WorkspaceAuthContext
from backend.exceptions import (
    ForbiddenError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)
from backend.repositories.attachment_repository import AttachmentRepository
from backend.repositories.task_repository import TaskRepository
from backend.security.abac import Action, PermissionContext, Resource, check_permission
from backend.services.audit_service import AuditService
from backend.settings import get_settings

_MAX_BYTES: Final[int] = 10 * 1024 * 1024
_DOWNLOAD_TTL_SECONDS: Final[int] = 15 * 60
_STORAGE_ROOT: Final[Path] = Path(".attachments")


def _safe_filename(filename: str) -> str:
    # Remove any path segments and normalize separators.
    name = Path(filename).name
    return name.replace(" ", "_")


def _is_allowed_mime(mime_type: str) -> bool:
    if mime_type.startswith("image/"):
        return True
    if mime_type in {"application/pdf", "text/plain"}:
        return True
    return False


class AttachmentSigner:
    """HMAC signer for time-bound download authorization."""

    def __init__(self, *, secret_key: str) -> None:
        self._secret = secret_key.encode("utf-8")

    def sign(self, *, attachment_id: UUID, expires_at: datetime) -> str:
        exp_ts = int(expires_at.replace(tzinfo=UTC).timestamp())
        msg = f"{attachment_id}:{exp_ts}".encode()
        sig = hmac.new(self._secret, msg, hashlib.sha256).hexdigest().encode()
        token_raw = msg + b":" + sig
        return base64.urlsafe_b64encode(token_raw).decode("utf-8").rstrip("=")

    def verify(self, *, attachment_id: UUID, token: str) -> None:
        try:
            padded = token + "=="[0 : (-len(token) % 4)]
            raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
            msg, sig = raw.rsplit(b":", 1)
            expected_sig = hmac.new(self._secret, msg, hashlib.sha256).hexdigest().encode("utf-8")
            if not hmac.compare_digest(sig, expected_sig):
                raise ValueError("bad signature")
            parts = msg.decode("utf-8").split(":")
            parsed_id = UUID(parts[0])
            exp_ts = int(parts[1])
        except Exception as exc:
            raise ForbiddenError("Invalid download token") from exc

        if parsed_id != attachment_id:
            raise ForbiddenError("Invalid download token")

        exp = datetime.fromtimestamp(exp_ts, tz=UTC)
        if datetime.now(UTC) >= exp:
            raise ForbiddenError("Download token expired")


class AttachmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._attachments = AttachmentRepository(session)
        self._tasks = TaskRepository(session)
        self._audit = AuditService()
        self._signer = AttachmentSigner(secret_key=get_settings().jwt_secret_key)

    async def _authorize_upload(self, *, ctx: WorkspaceAuthContext, task_id: UUID) -> None:
        task = await self._tasks.get_by_id_for_workspace(task_id, ctx.workspace_id)
        if task is None:
            raise NotFoundError("Task not found")

        can = check_permission(
            ctx.role,
            Resource.TASK,
            Action.UPDATE,
            actor_id=ctx.user.id,
            context=PermissionContext(owner_id=task.created_by, assignee_id=task.assignee_id),
        )
        if not can:
            raise ForbiddenError("Permission denied for attachment upload")
        return None

    async def upload(
        self,
        *,
        ctx: WorkspaceAuthContext,
        task_id: UUID,
        file: UploadFile,
    ) -> Attachment:
        await self._authorize_upload(ctx=ctx, task_id=task_id)

        mime_type = file.content_type or ""
        if not mime_type:
            guessed, _enc = mimetypes.guess_type(file.filename or "")
            mime_type = guessed or ""

        if not mime_type or not _is_allowed_mime(mime_type):
            raise UnsupportedMediaTypeError("Unsupported file type")

        data = await file.read()
        if len(data) > _MAX_BYTES:
            raise PayloadTooLargeError("File too large (max 10MB)")

        attachment_id = uuid4()
        safe_name = _safe_filename(file.filename or "upload")
        storage_key = f"{ctx.workspace_id}/{attachment_id}_{safe_name}"

        attachment = Attachment(
            id=attachment_id,
            workspace_id=ctx.workspace_id,
            task_id=task_id,
            uploaded_by=ctx.user.id,
            filename=safe_name,
            mime_type=mime_type,
            size_bytes=len(data),
            storage_key=storage_key,
        )
        self._session.add(attachment)
        await self._session.flush()

        target_path = _STORAGE_ROOT / storage_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

        await self._audit.log_event(
            actor_id=ctx.user.id,
            action="attachment.uploaded",
            resource_type="attachment",
            resource_id=attachment_id,
            metadata={
                "task_id": str(task_id),
                "mime_type": mime_type,
                "size_bytes": len(data),
            },
            workspace_id=ctx.workspace_id,
        )
        return attachment

    def make_download_token(self, *, attachment_id: UUID) -> tuple[str, datetime]:
        expires_at = datetime.now(UTC) + timedelta(seconds=_DOWNLOAD_TTL_SECONDS)
        token = self._signer.sign(attachment_id=attachment_id, expires_at=expires_at)
        return token, expires_at

    async def get_signed_download_url(self, *, attachment_id: UUID) -> str:
        token, _expires_at = self.make_download_token(attachment_id=attachment_id)
        # Relative URL so the frontend can prefix with NEXT_PUBLIC_API_URL.
        return f"/api/v1/attachments/{attachment_id}/download?token={token}"

    async def download_if_authorized(
        self,
        *,
        attachment_id: UUID,
        token: str,
    ) -> tuple[Path, Attachment]:
        self._signer.verify(attachment_id=attachment_id, token=token)
        attachment = await self._attachments.get_by_id(attachment_id)
        if attachment is None:
            raise NotFoundError("Attachment not found")

        path = _STORAGE_ROOT / attachment.storage_key
        if not path.exists():
            raise NotFoundError("Attachment file missing")

        return path, attachment

    async def list_for_task(
        self,
        *,
        ctx: WorkspaceAuthContext,
        task_id: UUID,
        limit: int,
        offset: int,
    ) -> list[Attachment]:
        task = await self._tasks.get_by_id_for_workspace(task_id, ctx.workspace_id)
        if task is None:
            raise NotFoundError("Task not found")

        if not check_permission(
            ctx.role,
            Resource.TASK,
            Action.READ,
            actor_id=ctx.user.id,
        ):
            raise ForbiddenError("Permission denied for attachment list")

        return await self._attachments.list_by_task(
            workspace_id=ctx.workspace_id,
            task_id=task_id,
            limit=limit,
            offset=offset,
        )
