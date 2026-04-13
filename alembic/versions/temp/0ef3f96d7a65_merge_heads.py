"""merge heads

Revision ID: 0ef3f96d7a65
Revises: 0ab0a33f2849, 6a98149157a1
Create Date: 2026-04-13 11:25:07.746359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ef3f96d7a65'
down_revision: Union[str, None] = ('0ab0a33f2849', '6a98149157a1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
