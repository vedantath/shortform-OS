"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trend_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("niche", sa.String(128), nullable=False),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("virality_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("engagement_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("monetization_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("saturation_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("opportunity_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("velocity", sa.Float, nullable=False, server_default="0"),
        sa.Column("raw_data", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("youtube_channel_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("posting_schedule", sa.Text, nullable=True),
        sa.Column("daily_upload_limit", sa.Integer, nullable=False, server_default="5"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("youtube_channel_id"),
    )

    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("user_prompt_template", sa.Text, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trend_signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Enum("pending", "scripting", "voicing", "fetching_visuals",
                                    "rendering", "uploading", "live", "failed",
                                    name="video_status"), nullable=False,
                  server_default="pending"),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tags", sa.Text, nullable=True),
        sa.Column("youtube_video_id", sa.String(32), nullable=True),
        sa.Column("local_path", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trend_signal_id"], ["trend_signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("content_json", sa.Text, nullable=False),
        sa.Column("model_used", sa.Text, nullable=False),
        sa.Column("prompt_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["prompt_template_id"], ["prompt_templates.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("views", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_watch_duration_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("retention_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float, nullable=False, server_default="0"),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("analytics")
    op.drop_table("scripts")
    op.drop_table("videos")
    op.execute("DROP TYPE IF EXISTS video_status")
    op.drop_table("prompt_templates")
    op.drop_table("channels")
    op.drop_table("trend_signals")
