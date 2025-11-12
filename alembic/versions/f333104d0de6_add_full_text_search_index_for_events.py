"""Add full-text search index for events

Revision ID: f333104d0de6
Revises: 67b9a1281bf9
Create Date: 2025-11-12 17:45:10.772690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f333104d0de6'
down_revision: Union[str, None] = '67b9a1281bf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create GIN index for full-text search on events table
    op.execute("""
        CREATE INDEX idx_event_search ON events 
        USING GIN (to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '')))
    """)


def downgrade() -> None:
    # Drop the full-text search index
    op.execute("DROP INDEX IF EXISTS idx_event_search")
