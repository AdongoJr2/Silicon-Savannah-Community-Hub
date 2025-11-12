"""Add category field to events

Revision ID: b410c0c51217
Revises: f333104d0de6
Create Date: 2025-11-12 17:47:44.966164

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b410c0c51217'
down_revision: Union[str, None] = 'f333104d0de6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create EventCategory enum type
    op.execute("""
        CREATE TYPE eventcategory AS ENUM (
            'technology', 'business', 'arts', 'sports', 
            'education', 'social', 'health', 'music', 'food', 'other'
        )
    """)
    
    # Add category column to events table
    op.execute("ALTER TABLE events ADD COLUMN category eventcategory")
    
    # Create index on category for filtering
    op.execute("CREATE INDEX idx_event_category ON events (category)")


def downgrade() -> None:
    # Drop the index and column
    op.execute("DROP INDEX IF EXISTS idx_event_category")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS category")
    op.execute("DROP TYPE IF EXISTS eventcategory")
