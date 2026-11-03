"""remove houses

Revision ID: 9e75ce6d4636
Revises: f3b1988d3fe7
Create Date: 2026-11-03 01:12:57.424981+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e75ce6d4636'
down_revision = 'f3b1988d3fe7'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('users', 'house')


def downgrade():
	op.add_column('users', sa.Column('house', sa.VARCHAR(length=16), autoincrement=False, nullable=True))
