"""remove user backgrounds

Revision ID: d1e116e8eea5
Revises: 85458909736a
Create Date: 2023-02-25 20:38:21.249379+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e116e8eea5'
down_revision = '85458909736a'
branch_labels = None
depends_on = None


def upgrade():
	# this first upgrade comand is non-reversible as some people may
	# intentionally choose the midnight theme. it isn't really that
	# destructive though as users can just... change it back.
	op.execute("UPDATE users SET theme='midnight' WHERE theme='transparent'")
	op.drop_column('users', 'background')


def downgrade():
	op.add_column('users', sa.Column('background', sa.VARCHAR(length=20), autoincrement=False, nullable=True))
