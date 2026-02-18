"""Replace date_of_birth with separate birth fields (year, month, day, time, place).

Revision ID: 004
Revises: 003
Create Date: 2025-02-18

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("birth_year", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("birth_month", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("birth_day", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("birth_time", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("birth_place", sa.String(255), nullable=True))
    op.drop_column("users", "date_of_birth")


def downgrade() -> None:
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.drop_column("users", "birth_place")
    op.drop_column("users", "birth_time")
    op.drop_column("users", "birth_day")
    op.drop_column("users", "birth_month")
    op.drop_column("users", "birth_year")
