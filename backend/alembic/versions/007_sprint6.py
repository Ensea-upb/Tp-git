"""Sprint 6 — Pipeline de candidatures

Revision ID: 007
Revises: 006
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── applications ──────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "offer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("offers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="DRAFT"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_channel", sa.String(255), nullable=True),
        sa.Column("draft_cover_letter", sa.Text, nullable=True),
        sa.Column("draft_email", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_applications_offer_id", "applications", ["offer_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    # ── application_followups ─────────────────────────────────────────
    op.create_table(
        "application_followups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_application_followups_application_id",
        "application_followups",
        ["application_id"],
    )


def downgrade() -> None:
    op.drop_table("application_followups")
    op.drop_table("applications")
