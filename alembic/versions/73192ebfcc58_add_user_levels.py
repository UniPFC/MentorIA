"""add user levels

Revision ID: 73192ebfcc58
Revises: 944912616179
Create Date: 2026-05-17 19:48:52.771272

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "73192ebfcc58"
down_revision: str | Sequence[str] | None = "944912616179"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user level enum type first (PostgreSQL requires this)
    user_level_enum = sa.Enum(
        "LEVEL_01", "LEVEL_02", "LEVEL_03", "LEVEL_04", "LEVEL_05", name="userlevel"
    )
    user_level_enum.create(op.get_bind(), checkfirst=True)

    # Add columns to users table
    op.add_column(
        "users",
        sa.Column("level", user_level_enum, nullable=False, server_default="LEVEL_01"),
    )
    op.add_column("users", sa.Column("token_budget", sa.Integer(), nullable=True))

    # Set default budget and level for existing users
    # Import settings to get the default budget value
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from config.settings import settings

    op.execute(
        f"UPDATE users SET token_budget = {settings.TOKEN_BUDGET_LEVEL_01} WHERE token_budget IS NULL"
    )
    op.execute("UPDATE users SET level = 'LEVEL_01' WHERE level IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "token_budget")
    op.drop_column("users", "level")
    sa.Enum(name="userlevel").drop(op.get_bind(), checkfirst=True)
