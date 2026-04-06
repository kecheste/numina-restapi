"""Add input_json and updated_at to user_synthesis.

Stores the two-layer signal payload (core + dynamic module fingerprints) that was
used to produce result_json. Enables incremental merging when a new test completes
instead of re-extracting all signals from scratch.

Revision ID: 017
Revises: 20260402_0947_4fc1f7c9f584
Create Date: 2026-04-05

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "017_synthesis_input_json"
down_revision: str | None = "4fc1f7c9f584"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_synthesis",
        sa.Column("input_json", JSONB, nullable=True),
    )
    op.add_column(
        "user_synthesis",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_synthesis", "updated_at")
    op.drop_column("user_synthesis", "input_json")
