"""add voiced, voice_skipped, footage_ready, footage_skipped to video_status

Adds the four new pipeline statuses introduced by the voice synthesis and
visual fetch workers.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL 12+ supports ALTER TYPE ... ADD VALUE inside a transaction.
    # IF NOT EXISTS makes each statement idempotent on re-run.
    op.execute(
        "ALTER TYPE video_status ADD VALUE IF NOT EXISTS 'voiced' AFTER 'voicing'"
    )
    op.execute(
        "ALTER TYPE video_status ADD VALUE IF NOT EXISTS 'voice_skipped' AFTER 'voiced'"
    )
    op.execute(
        "ALTER TYPE video_status ADD VALUE IF NOT EXISTS 'footage_ready' AFTER 'fetching_visuals'"
    )
    op.execute(
        "ALTER TYPE video_status ADD VALUE IF NOT EXISTS 'footage_skipped' AFTER 'footage_ready'"
    )


def downgrade() -> None:
    # PostgreSQL has no DROP VALUE — the only option is to recreate the type.
    # Rows in any of the new statuses are demoted to 'failed' first to avoid
    # cast errors when the type is narrowed.
    op.execute(
        "UPDATE videos SET status = 'failed'"
        " WHERE status::text IN"
        " ('voiced', 'voice_skipped', 'footage_ready', 'footage_skipped')"
    )

    # Widen to text so the column survives the type drop.
    op.execute(
        "ALTER TABLE videos"
        "    ALTER COLUMN status TYPE varchar(32)"
        "    USING status::text"
    )

    op.execute("DROP TYPE video_status")

    # Recreate at the 0002 state.
    op.execute(
        """
        CREATE TYPE video_status AS ENUM (
            'pending',
            'scripting',
            'scripted',
            'voicing',
            'fetching_visuals',
            'rendering',
            'uploading',
            'live',
            'failed'
        )
        """
    )

    op.execute(
        "ALTER TABLE videos"
        "    ALTER COLUMN status TYPE video_status"
        "    USING status::video_status"
    )
