"""Attachment routes (TF-014)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.schemas.attachment import (
    AttachmentListResponse,
    AttachmentResponse,
    SignedDownloadUrlResponse,
)
from backend.services.attachment_service import AttachmentService

router = APIRouter(tags=["attachments"])


def get_attachment_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AttachmentService:
    return AttachmentService(session)


@router.post(
    "/tasks/{task_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    task_id: UUID,
    file: Annotated[UploadFile, File()],
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[AttachmentService, Depends(get_attachment_service)],
) -> AttachmentResponse:
    attachment = await service.upload(ctx=ctx, task_id=task_id, file=file)
    download_url = await service.get_signed_download_url(attachment_id=attachment.id)
    return AttachmentResponse(
        id=attachment.id,
        workspace_id=attachment.workspace_id,
        task_id=attachment.task_id,
        uploaded_by=attachment.uploaded_by,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        storage_key=attachment.storage_key,
        created_at=attachment.created_at,
        download_url=download_url,
    )


@router.get(
    "/tasks/{task_id}/attachments",
    response_model=AttachmentListResponse,
)
async def list_task_attachments(
    task_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[AttachmentService, Depends(get_attachment_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AttachmentListResponse:
    attachments = await service.list_for_task(
        ctx=ctx,
        task_id=task_id,
        limit=limit,
        offset=offset,
    )

    items: list[AttachmentResponse] = []
    for attachment in attachments:
        download_url = await service.get_signed_download_url(attachment_id=attachment.id)
        items.append(
            AttachmentResponse(
                id=attachment.id,
                workspace_id=attachment.workspace_id,
                task_id=attachment.task_id,
                uploaded_by=attachment.uploaded_by,
                filename=attachment.filename,
                mime_type=attachment.mime_type,
                size_bytes=attachment.size_bytes,
                storage_key=attachment.storage_key,
                created_at=attachment.created_at,
                download_url=download_url,
            )
        )

    return AttachmentListResponse(items=items, limit=limit, offset=offset)


@router.get("/attachments/{attachment_id}/download", response_model=None)
async def download_attachment(
    attachment_id: UUID,
    service: Annotated[AttachmentService, Depends(get_attachment_service)],
    token: Annotated[str | None, Query()] = None,
) -> Any:
    # If no token is provided, we return a signed URL that the caller can use.
    if token is None:
        download_url = await service.get_signed_download_url(attachment_id=attachment_id)
        return SignedDownloadUrlResponse(download_url=download_url)

    path, attachment = await service.download_if_authorized(
        attachment_id=attachment_id,
        token=token,
    )

    return FileResponse(
        path=str(path),
        media_type=attachment.mime_type,
        filename=attachment.filename,
    )
