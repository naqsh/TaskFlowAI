"""Attachment request/response schemas (TF-014)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttachmentResponse(BaseModel):
    """Attachment metadata returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    task_id: UUID
    uploaded_by: UUID | None
    filename: str
    mime_type: str
    size_bytes: int
    storage_key: str
    created_at: datetime
    download_url: str = Field(..., description="Signed download URL (relative to API base).")


class SignedDownloadUrlResponse(BaseModel):
    """Response containing a signed download URL."""

    download_url: str


class AttachmentListResponse(BaseModel):
    """Paginated attachment list for a task."""

    model_config = ConfigDict(from_attributes=True)

    items: list[AttachmentResponse]
    limit: int
    offset: int
