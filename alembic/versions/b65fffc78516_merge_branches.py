"""merge branches

Revision ID: b65fffc78516
Revises: 3f8087f17f0a, 5e82f25771bc
Create Date: 2026-06-08 14:30:36.760157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b65fffc78516'
down_revision: Union[str, Sequence[str], None] = ('3f8087f17f0a', '5e82f25771bc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
