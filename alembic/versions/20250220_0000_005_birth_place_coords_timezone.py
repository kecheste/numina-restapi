"""Add birth_place_lat, birth_place_lng, birth_place_timezone for Mapbox-resolved location.

Revision ID: 005
Revises: 004
Create Date: 2025-02-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _users_columns():
    bind = op.get_bind()
    insp = inspect(bind)
    return {c["name"] for c in insp.get_columns("users")}


def upgrade() -> None:
    cols = _users_columns()
    if "birth_place_lat" not in cols:
        op.add_column("users", sa.Column("birth_place_lat", sa.Float(), nullable=True))
    if "birth_place_lng" not in cols:
        op.add_column("users", sa.Column("birth_place_lng", sa.Float(), nullable=True))
    if "birth_place_timezone" not in cols:
        op.add_column("users", sa.Column("birth_place_timezone", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "birth_place_timezone")
    op.drop_column("users", "birth_place_lng")
    op.drop_column("users", "birth_place_lat")
