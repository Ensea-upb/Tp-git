"""Sprint 4 — user_preferences, offer_user_statuses, personalized scoring fields

Revision ID: 004
Revises: 003
Create Date: 2026-03-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Table user_preferences ────────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("preferred_contract_types", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("preferred_work_modes", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("preferred_locations", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("preferred_keywords", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("preferred_domains", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("exclude_keywords", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("minimum_duration_months", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── Table offer_user_statuses ─────────────────────────────────────
    op.create_table(
        "offer_user_statuses",
        sa.Column(
            "offer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("offers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_offer_user_statuses_status", "offer_user_statuses", ["status"])

    # ── Colonnes scoring personnalisé sur offers ───────────────────────
    op.add_column(
        "offers",
        sa.Column("personalized_score", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "offers",
        sa.Column("personalized_justification", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("offers", "personalized_justification")
    op.drop_column("offers", "personalized_score")
    op.drop_index("ix_offer_user_statuses_status", table_name="offer_user_statuses")
    op.drop_table("offer_user_statuses")
    op.drop_table("user_preferences")
