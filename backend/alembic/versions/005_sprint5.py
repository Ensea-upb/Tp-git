"""Sprint 5 — LLM copilot tables

Revision ID: 005
Revises: 004
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # llm_cache — SHA-256(model:prompt) → response
    op.create_table(
        "llm_cache",
        sa.Column("cache_key", sa.Text, primary_key=True),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("prompt_hash", sa.Text, nullable=False),
        sa.Column("response_text", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_llm_cache_created_at", "llm_cache", ["created_at"])

    # offer_llm_analyses — structured analysis per offer
    op.create_table(
        "offer_llm_analyses",
        sa.Column(
            "offer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("offers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model_used", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("missions", JSONB, nullable=True),      # list[str]
        sa.Column("skills_required", JSONB, nullable=True),  # list[str]
        sa.Column("tech_stack", JSONB, nullable=True),    # list[str]
        sa.Column("seniority_level", sa.Text, nullable=True),
        sa.Column("raw_response", sa.Text, nullable=True),
        sa.Column("analysis_status", sa.Text, nullable=False, server_default="PENDING"),
        sa.Column(
            "analyzed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # candidate_profiles — singleton "who am I"
    op.create_table(
        "candidate_profiles",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("full_name", sa.Text, nullable=True),
        sa.Column("current_level", sa.Text, nullable=True),   # e.g. "Master 2 Data Science"
        sa.Column("school", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),          # free-text bio
        sa.Column("skills", JSONB, nullable=True),             # list[str]
        sa.Column("tech_stack", JSONB, nullable=True),         # list[str]
        sa.Column("languages", JSONB, nullable=True),          # list[str]
        sa.Column("experiences", JSONB, nullable=True),        # list[{title,company,duration,description}]
        sa.Column("projects", JSONB, nullable=True),           # list[{name,description,tech}]
        sa.Column("target_domains", JSONB, nullable=True),     # list[str]
        sa.Column("availability", sa.Text, nullable=True),     # e.g. "March 2026"
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # profile_match_llm — LLM-based offer × profile match
    op.create_table(
        "profile_match_llm",
        sa.Column(
            "offer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("offers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model_used", sa.Text, nullable=False),
        sa.Column("match_score", sa.Numeric(5, 2), nullable=True),   # 0–100
        sa.Column("strengths", JSONB, nullable=True),                 # list[str]
        sa.Column("gaps", JSONB, nullable=True),                      # list[str]
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("raw_response", sa.Text, nullable=True),
        sa.Column("match_status", sa.Text, nullable=False, server_default="PENDING"),
        sa.Column(
            "matched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("profile_match_llm")
    op.drop_table("offer_llm_analyses")
    op.drop_table("candidate_profiles")
    op.drop_index("ix_llm_cache_created_at", table_name="llm_cache")
    op.drop_table("llm_cache")
