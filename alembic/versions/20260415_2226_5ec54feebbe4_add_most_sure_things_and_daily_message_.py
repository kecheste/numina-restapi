"""add_most_sure_things_and_daily_message_cache

Revision ID: 5ec54feebbe4
Revises: 017_synthesis_input_json
Create Date: 2026-04-15 22:26:00.824416

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5ec54feebbe4'
down_revision: Union[str, None] = '017_synthesis_input_json'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('most_sure_things', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('daily_message_cache', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'daily_message_cache')
    op.drop_column('users', 'most_sure_things')
