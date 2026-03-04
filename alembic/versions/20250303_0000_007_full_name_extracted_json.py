"""Add users.full_name and test_results.extracted_json.

Revision ID: 007
Revises: 006
Create Date: 2025-03-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "test_results",
        sa.Column("extracted_json", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("test_results", "extracted_json")
    op.drop_column("users", "full_name")
