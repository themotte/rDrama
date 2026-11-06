"""drop users.defaulttime

Revision ID: e8b2c4d6f1a3
Revises: d3f1a9c2e7b4
Create Date: 2026-11-06 12:10:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8b2c4d6f1a3'
down_revision = 'd3f1a9c2e7b4'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('users', 'defaulttime')


def downgrade():
	op.add_column('users', sa.Column('defaulttime', sa.VARCHAR(length=5), server_default='all', autoincrement=False, nullable=False))
	op.alter_column('users', 'defaulttime', server_default=None)
