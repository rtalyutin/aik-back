"""create_karaoke_tracks_tables

Revision ID: 2c8da5dda8b2
Revises: 9d08d40f4a35
Create Date: 2025-10-31 14:41:12.622459

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "2c8da5dda8b2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблица треков
    op.create_table(
        "karaoke_tracks",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("base_track_file", sa.String(), nullable=False),
        sa.Column("vocal_file", sa.String(), nullable=False),
        sa.Column("instrumental_file", sa.String(), nullable=False),
        sa.Column("lang_code", sa.String(length=10), nullable=False),
        sa.Column("transcript", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )

    # Таблица задач
    op.create_table(
        "karaoke_track_creating_tasks",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("base_track_file", sa.String(), nullable=False),
        sa.Column("result_track_id", sa.UUID(), nullable=True),
        sa.Column("vocal_file", sa.String(), nullable=True),
        sa.Column("instrumental_file", sa.String(), nullable=True),
        sa.Column("words", JSONB(), nullable=True),
        sa.Column("subtitles", JSONB(), nullable=True),
        sa.Column("lang_code", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.ForeignKeyConstraint(
            ["result_track_id"],
            ["karaoke_tracks.id"],
        ),
    )

    # Таблица задач
    op.create_table(
        "karaoke_track_creating_task_steps",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("task_id", sa.UUID()),
        sa.Column("data", JSONB(), nullable=True),
        sa.Column("step", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["karaoke_track_creating_tasks.id"],
        ),
    )

    # Таблица логов
    op.create_table(
        "karaoke_track_creating_task_logs",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("step_id", sa.UUID(), nullable=True),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["karaoke_track_creating_tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["karaoke_track_creating_task_steps.id"],
        ),
    )


def downgrade() -> None:
    op.drop_table("karaoke_track_creating_task_logs")
    op.drop_table("karaoke_track_creating_task_steps")
    op.drop_table("karaoke_track_creating_tasks")
    op.drop_table("karaoke_tracks")
