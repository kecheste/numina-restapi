"""Add user profile columns (name, date_of_birth, is_premium, subscription, updated_at).

Revision ID: 002
Revises: 001
Create Date: 2025-02-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'free'"),
        ),
    )
    op.add_column("users", sa.Column("subscription_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "updated_at")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "subscription_id")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "is_premium")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "name")
