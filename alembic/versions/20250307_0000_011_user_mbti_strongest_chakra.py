"""Add users.mbti_type, mbti_descriptor, strongest_chakra for onboarding MBTI and Chakra results.

Revision ID: 011
Revises: 010
Create Date: 2025-03-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("mbti_type", sa.String(20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mbti_descriptor", sa.String(100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("strongest_chakra", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "strongest_chakra")
    op.drop_column("users", "mbti_descriptor")
    op.drop_column("users", "mbti_type")
