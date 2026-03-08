"""Add users.soul_urge_number, birthday_number, expression_number for numerology blueprint.

Revision ID: 012
Revises: 011
Create Date: 2025-03-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("soul_urge_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("birthday_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("expression_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "expression_number")
    op.drop_column("users", "birthday_number")
    op.drop_column("users", "soul_urge_number")
