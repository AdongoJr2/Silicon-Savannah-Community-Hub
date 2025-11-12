"""Initial migration with indexes and constraints

Revision ID: 67b9a1281bf9
Revises: 
Create Date: 2025-11-12 17:15:36.066504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '67b9a1281bf9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create role enum
    role_enum = postgresql.ENUM('user', 'organizer', 'admin', name='roleenum')
    role_enum.create(op.get_bind())
    
    # Create rsvp status enum
    rsvp_status_enum = postgresql.ENUM('going', 'interested', 'cancelled', name='rsvpstatusenum')
    rsvp_status_enum.create(op.get_bind())
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('user', 'organizer', 'admin', name='roleenum'), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('capacity', sa.Integer, nullable=True, server_default='0'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('idx_event_date', 'events', ['starts_at'])
    op.create_index('idx_event_organizer', 'events', ['created_by'])
    op.create_index('idx_event_created_at', 'events', ['created_at'])
    
    # Create rsvps table
    op.create_table(
        'rsvps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id'), nullable=False),
        sa.Column('status', sa.Enum('going', 'interested', 'cancelled', name='rsvpstatusenum'), nullable=False, server_default='going'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('idx_rsvp_user', 'rsvps', ['user_id'])
    op.create_index('idx_rsvp_event', 'rsvps', ['event_id'])
    op.create_unique_constraint('uq_user_event_rsvp', 'rsvps', ['user_id', 'event_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('rsvps')
    op.drop_table('events')
    op.drop_table('users')
    
    # Drop enums
    sa.Enum(name='rsvpstatusenum').drop(op.get_bind())
    sa.Enum(name='roleenum').drop(op.get_bind())
