"""add ranking_score to offers

Revision ID: 009
Revises: 008
Create Date: 2026-03-16

Sprint 8 — OfferRankingService : score composite de pertinence 0-100.
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "offers",
        sa.Column("ranking_score", sa.Numeric(5, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("offers", "ranking_score")
