"""base_init_table

Revision ID: 9d08d40f4a35
Revises:
Create Date: 2025-10-30 13:19:41.583648

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "9d08d40f4a35"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_matcher_vacancies",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column(
            "source_id",
            sa.UUID(),
            index=True,
            nullable=True,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "company",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "job_title",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "specialist_type",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "work_format",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "grade",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "experience_required",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "salary",
            JSONB(),
            nullable=True,
        ),
        sa.Column(
            "technologies",
            JSONB(),
            nullable=False,
        ),
        sa.Column(
            "skills",
            JSONB(),
            nullable=False,
        ),
        sa.Column("duplicate_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("original_vacancy_id", sa.UUID(), nullable=True),
        sa.Column("duplicate_check_success", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_table(
        "job_matcher_source_process_logs",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column(
            "source_id",
            sa.UUID(),
            index=True,
            nullable=True,
        ),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("is_vacancy", sa.Boolean(), nullable=True),
        sa.Column(
            "data",
            JSONB(),
        ),
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
    op.create_table(
        "job_matcher_resumes",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "employee",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "specialist_type",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "grade",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "experience",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "salary",
            JSONB(),
            nullable=True,
        ),
        sa.Column(
            "technologies",
            JSONB(),
            nullable=False,
        ),
        sa.Column(
            "skills",
            JSONB(),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
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
    op.create_table(
        "job_matcher_vacancy_with_resume_matches",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "vacancy_id",
            sa.UUID(),
            sa.ForeignKey("job_matcher_vacancies.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column(
            "resume_id",
            sa.UUID(),
            sa.ForeignKey("job_matcher_resumes.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column(
            "comments",
            JSONB(),
            nullable=False,
        ),
        sa.Column(
            "is_recommended", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("vacancy_id", "resume_id"),
    )
    op.create_table(
        "job_matcher_vacancy_with_resume_match_process_logs",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "vacancy_id",
            sa.UUID(),
            index=True,
            nullable=False,
        ),
        sa.Column(
            "resume_id",
            sa.UUID(),
            index=True,
            nullable=False,
        ),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column(
            "data",
            JSONB(),
        ),
        sa.Column("is_recommended", sa.Boolean(), nullable=True),
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
    op.create_table(
        "job_matcher_vacancy_duplicate_check_process_logs",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "vacancy_id",
            sa.UUID(),
            index=True,
            nullable=False,
        ),
        sa.Column("is_duplicate", sa.Boolean(), nullable=True),
        sa.Column(
            "duplicate_of_vacancy_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "data",
            JSONB(),
            nullable=False,
        ),
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


def downgrade() -> None:
    op.drop_table("job_matcher_vacancy_duplicate_check_process_logs")
    op.drop_table("job_matcher_vacancy_with_resume_match_process_logs")
    op.drop_table("job_matcher_vacancy_with_resume_matches")
    op.drop_table("job_matcher_resumes")
    op.drop_table("job_matcher_source_process_logs")
    op.drop_table("job_matcher_vacancies")
