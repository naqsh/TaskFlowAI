"""Alembic migration: DLQ events, quarantine table, audit seal columns (TF-E4)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_security_layer1"
down_revision: str | None = "005_episodic_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dlq_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column(
            "envelope_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_dlq_events_request_id", "dlq_events", ["request_id"])
    op.create_index("ix_dlq_events_reason", "dlq_events", ["reason"])

    op.create_table(
        "quarantined_mcp_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tool", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("raw_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_quarantined_mcp_responses_tool", "quarantined_mcp_responses", ["tool"])
    op.create_index(
        "ix_quarantined_mcp_responses_raw_hash", "quarantined_mcp_responses", ["raw_hash"]
    )

    op.add_column("audit_logs", sa.Column("prev_hash", sa.String(length=64), nullable=True))
    op.add_column("audit_logs", sa.Column("entry_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_audit_logs_entry_hash", "audit_logs", ["entry_hash"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entry_hash", table_name="audit_logs")
    op.drop_column("audit_logs", "entry_hash")
    op.drop_column("audit_logs", "prev_hash")
    op.drop_table("quarantined_mcp_responses")
    op.drop_index("ix_dlq_events_reason", table_name="dlq_events")
    op.drop_index("ix_dlq_events_request_id", table_name="dlq_events")
    op.drop_table("dlq_events")
