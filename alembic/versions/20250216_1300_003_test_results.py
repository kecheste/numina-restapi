"""Create test_results table.

Revision ID: 003
Revises: 002
Create Date: 2025-02-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "test_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("test_title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("answers", JSONB, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending_ai'")),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("personality_type", sa.String(100), nullable=True),
        sa.Column("insights", JSONB, nullable=True),
        sa.Column("recommendations", JSONB, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_results_user_id"), "test_results", ["user_id"], unique=False)
    op.create_index(op.f("ix_test_results_test_id"), "test_results", ["test_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_test_results_test_id"), table_name="test_results")
    op.drop_index(op.f("ix_test_results_user_id"), table_name="test_results")
    op.drop_table("test_results")
