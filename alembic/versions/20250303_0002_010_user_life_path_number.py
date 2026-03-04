"""Add users.life_path_number for onboarding Life Path (19) result.

Revision ID: 010
Revises: 009
Create Date: 2025-03-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("life_path_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "life_path_number")
