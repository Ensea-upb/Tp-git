"""Initial schema: sources, companies, offers

Revision ID: 001
Revises:
Create Date: 2026-03-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Table sources
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("base_url", sa.String(2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("check_frequency_hours", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("legal_status", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Table companies
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(255), nullable=True),
        sa.Column("website_url", sa.String(2048), nullable=True),
        sa.Column("main_location", sa.String(255), nullable=True),
        sa.Column("priority_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("company_status", sa.String(50), nullable=False, server_default="neutre"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_companies_name", "companies", ["name"])

    # Table offers
    op.create_table(
        "offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("primary_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("normalized_title", sa.String(512), nullable=False),
        sa.Column("normalized_description", sa.Text(), nullable=True),
        sa.Column("contract_type", sa.String(100), nullable=True),
        sa.Column("duration_months", sa.Integer(), nullable=True),
        sa.Column("location_text", sa.String(255), nullable=True),
        sa.Column("work_mode", sa.String(50), nullable=True),
        sa.Column("education_level", sa.String(100), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_state", sa.String(50), nullable=False, server_default="DETECTED"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("global_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("action_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_justification", postgresql.JSONB(), nullable=True),
        sa.Column("offer_url", sa.String(2048), nullable=True, unique=True),
        sa.Column("external_offer_id", sa.String(255), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("semantic_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_offers_current_state", "offers", ["current_state"])
    op.create_index("ix_offers_is_active", "offers", ["is_active"])
    op.create_index("ix_offers_company_id", "offers", ["company_id"])
    op.create_index("ix_offers_primary_source_id", "offers", ["primary_source_id"])


def downgrade() -> None:
    op.drop_table("offers")
    op.drop_table("companies")
    op.drop_table("sources")
