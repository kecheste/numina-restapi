"""Add test_results.llm_result_json and user_synthesis table.

Revision ID: 008
Revises: 007
Create Date: 2025-03-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_results",
        sa.Column("llm_result_json", JSONB, nullable=True),
    )
    op.create_table(
        "user_synthesis",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("synthesis_type", sa.String(20), nullable=False),
        sa.Column("result_json", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "synthesis_type", name="uq_user_synthesis_user_type"),
    )
    op.create_index("ix_user_synthesis_user_id", "user_synthesis", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_synthesis_user_id", table_name="user_synthesis")
    op.drop_table("user_synthesis")
    op.drop_column("test_results", "llm_result_json")
