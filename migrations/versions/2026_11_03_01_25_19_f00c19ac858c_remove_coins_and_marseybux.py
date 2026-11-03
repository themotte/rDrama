"""remove coins and marseybux

Revision ID: f00c19ac858c
Revises: 9e75ce6d4636
Create Date: 2026-11-03 01:25:19.666574+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f00c19ac858c'
down_revision = '9e75ce6d4636'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('users', 'coins')
	op.drop_column('users', 'procoins')

	op.execute("DELETE FROM modactions WHERE kind = 'monthly'")


def downgrade():
	op.add_column('users', sa.Column('procoins', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
	op.add_column('users', sa.Column('coins', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
