"""Suppression de la colonne action_score (jamais utilisée)

Revision ID: 006
Revises: 005
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import NUMERIC

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("offers", "action_score")


def downgrade() -> None:
    op.add_column(
        "offers",
        sa.Column("action_score", NUMERIC(5, 2), nullable=True),
    )
