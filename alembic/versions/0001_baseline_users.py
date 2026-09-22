"""Baseline: the users table as it exists today.

This revision reproduces the pre-migration schema so an existing database can
be stamped instead of rebuilt:

    alembic stamp 0001_baseline_users

On a fresh database, run it normally with `alembic upgrade head`.

Revision ID: 0001_baseline_users
Revises:
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline_users"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Matches the old models/user.py: three roles, loose nullability.
    # sa.Enum inside create_table emits CREATE TYPE automatically.
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fullname", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "INSTRUCTOR", "STUDENT", name="userrole"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
