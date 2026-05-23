"""add scripted to video_status enum

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-22 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL 9.3+: IF NOT EXISTS makes this idempotent on re-run.
    op.execute("ALTER TYPE video_status ADD VALUE IF NOT EXISTS 'scripted' AFTER 'scripting'")


def downgrade() -> None:
    # PostgreSQL has no DROP VALUE — recreate the type without 'scripted'.
    op.execute("""
        ALTER TABLE videos
            ALTER COLUMN status TYPE varchar(32)
            USING status::text;
    """)
    op.execute("DROP TYPE video_status")
    op.execute("""
        CREATE TYPE video_status AS ENUM (
            'pending', 'scripting', 'voicing',
            'fetching_visuals', 'rendering',
            'uploading', 'live', 'failed'
        )
    """)
    op.execute("""
        ALTER TABLE videos
            ALTER COLUMN status TYPE video_status
            USING status::video_status;
    """)
