"""Add offers_raw table and raw_offer_id to offers

Revision ID: 002
Revises: 001
Create Date: 2026-03-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Table offers_raw
    op.create_table(
        "offers_raw",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id"),
            nullable=False,
        ),
        sa.Column("external_offer_id", sa.Text(), nullable=True),
        sa.Column("offer_url", sa.Text(), nullable=True, unique=True),
        sa.Column("raw_title", sa.Text(), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("raw_location", sa.Text(), nullable=True),
        sa.Column("raw_company_name", sa.Text(), nullable=True),
        sa.Column("published_at_detected", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("parsing_status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_offers_raw_source_id", "offers_raw", ["source_id"])
    op.create_index("ix_offers_raw_parsing_status", "offers_raw", ["parsing_status"])
    op.create_index(
        "ix_offers_raw_source_external",
        "offers_raw",
        ["source_id", "external_offer_id"],
        unique=False,
    )

    # Ajouter raw_offer_id sur offers (lien de traçabilité)
    op.add_column(
        "offers",
        sa.Column(
            "raw_offer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("offers_raw.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_offers_raw_offer_id", "offers", ["raw_offer_id"])


def downgrade() -> None:
    op.drop_index("ix_offers_raw_offer_id", table_name="offers")
    op.drop_column("offers", "raw_offer_id")
    op.drop_table("offers_raw")
