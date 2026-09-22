"""Collapse roles to ADMIN/USER and tighten the users table.

Every non-ADMIN row (INSTRUCTOR *and* STUDENT) becomes USER.

Deliberate decision: existing INSTRUCTOR rows are NOT promoted to ADMIN.
Registration previously accepted a client-supplied `role`, so any INSTRUCTOR
row may have been self-assigned by an anonymous signup. Demote everyone, then
promote real admins deliberately via scripts/seed_admin.py.

Record the before-state first:
    SELECT role, count(*) FROM users GROUP BY role;

Revision ID: 0002_roles_admin_user
Revises: 0001_baseline_users
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_roles_admin_user"
down_revision: Union[str, None] = "0001_baseline_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill NULLs before the column becomes NOT NULL.
    op.execute("UPDATE users SET role = 'STUDENT' WHERE role IS NULL")
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE users SET fullname = '' WHERE fullname IS NULL")

    # Swap the enum type in place. The USING clause maps ADMIN->ADMIN and
    # everything else (INSTRUCTOR, STUDENT) -> USER.
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM ('ADMIN', 'USER')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING (CASE WHEN role::text = 'ADMIN' THEN 'ADMIN' ELSE 'USER' END)::userrole"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'USER'")
    op.execute("DROP TYPE userrole_old")

    op.alter_column("users", "role", nullable=False)
    op.alter_column(
        "users",
        "is_active",
        nullable=False,
        server_default=sa.text("true"),
    )
    op.alter_column(
        "users",
        "fullname",
        existing_type=sa.String(length=50),
        type_=sa.String(length=100),
        nullable=False,
    )
    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    # Irreversible in substance: INSTRUCTOR/STUDENT cannot be recovered, since
    # the distinction was destroyed on upgrade. Everyone lands on STUDENT.
    op.alter_column("users", "email", existing_type=sa.String(), nullable=True)
    op.alter_column(
        "users",
        "fullname",
        existing_type=sa.String(length=100),
        type_=sa.String(length=50),
        nullable=True,
    )
    op.alter_column("users", "is_active", nullable=True)
    op.alter_column("users", "role", nullable=True)

    op.execute("ALTER TYPE userrole RENAME TO userrole_new")
    op.execute("CREATE TYPE userrole AS ENUM ('ADMIN', 'INSTRUCTOR', 'STUDENT')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING (CASE WHEN role::text = 'ADMIN' THEN 'ADMIN' ELSE 'STUDENT' END)::userrole"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'STUDENT'")
    op.execute("DROP TYPE userrole_new")
