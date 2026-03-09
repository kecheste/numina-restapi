"""Drop users.birthday_number; value is derived from birth_day when needed.

Revision ID: 013
Revises: 012
Create Date: 2025-03-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("users", "birthday_number")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("birthday_number", sa.Integer(), nullable=True),
    )
