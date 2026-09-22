"""Add users.token_version for access-token revocation.

Revision ID: 0004_user_token_version
Revises: 0003_catalog_and_submissions
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_user_token_version"
down_revision: Union[str, None] = "0003_catalog_and_submissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
