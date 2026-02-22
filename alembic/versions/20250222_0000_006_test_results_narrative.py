"""Add narrative column to test_results (LLM-generated prose from computed result).

Revision ID: 006
Revises: 005
Create Date: 2025-02-22

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_results",
        sa.Column("narrative", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("test_results", "narrative")
