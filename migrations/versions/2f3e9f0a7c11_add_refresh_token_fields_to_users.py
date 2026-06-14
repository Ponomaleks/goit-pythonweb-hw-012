"""add refresh token fields to users

Revision ID: 2f3e9f0a7c11
Revises: 09328acea8bf
Create Date: 2026-06-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f3e9f0a7c11"
down_revision: Union[str, Sequence[str], None] = "09328acea8bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "users", sa.Column("refresh_token_hash", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("users", "refresh_token_expires_at")
    op.drop_column("users", "refresh_token_hash")