"""Add episodic memory table (TF-E3 Part 1)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_episodic_memory"
down_revision: str | None = "004_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "episodic_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(length=200), nullable=False),
        sa.Column("lesson_type", sa.String(length=120), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_episodic_entries_user_id", "episodic_entries", ["user_id"])
    op.create_index("ix_episodic_entries_session_id", "episodic_entries", ["session_id"])
    op.create_index("ix_episodic_entries_lesson_type", "episodic_entries", ["lesson_type"])


def downgrade() -> None:
    op.drop_index("ix_episodic_entries_lesson_type", table_name="episodic_entries")
    op.drop_index("ix_episodic_entries_session_id", table_name="episodic_entries")
    op.drop_index("ix_episodic_entries_user_id", table_name="episodic_entries")
    op.drop_table("episodic_entries")

