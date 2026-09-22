"""Reference catalog, submissions, and analyses.

Revision ID: 0003_catalog_and_submissions
Revises: 0002_roles_admin_user
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_catalog_and_submissions"
down_revision: Union[str, None] = "0002_roles_admin_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reference_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("repo_url", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reference_projects_name"), "reference_projects", ["name"], unique=True
    )

    op.create_table(
        "reference_branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_name", sa.String(length=255), nullable=False),
        sa.Column("collection_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "indexing", "ready", "failed", name="branchstatus"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("files_indexed", sa.Integer(), nullable=True),
        sa.Column("chunks_indexed", sa.Integer(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["reference_projects.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "branch_name", name="uq_reference_branch"),
        sa.UniqueConstraint("collection_name"),
    )
    op.create_index(
        op.f("ix_reference_branches_project_id"),
        "reference_branches",
        ["project_id"],
    )
    op.create_index(
        op.f("ix_reference_branches_status"), "reference_branches", ["status"]
    )

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("file_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_submissions_owner_id"), "submissions", ["owner_id"])
    op.create_index(op.f("ix_submissions_created_at"), "submissions", ["created_at"])

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("success", "failed", name="analysisstatus"),
            nullable=False,
        ),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["reference_branches.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyses_submission_id"), "analyses", ["submission_id"])
    op.create_index(op.f("ix_analyses_created_at"), "analyses", ["created_at"])


def downgrade() -> None:
    op.drop_table("analyses")
    op.drop_table("submissions")
    op.drop_table("reference_branches")
    op.drop_index(op.f("ix_reference_projects_name"), table_name="reference_projects")
    op.drop_table("reference_projects")
    sa.Enum(name="analysisstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="branchstatus").drop(op.get_bind(), checkfirst=True)
