"""remove reddit, nitter and controversial link preferences

Revision ID: dc780b606a2a
Revises: ecdecbff60df
Create Date: 2026-11-03 02:59:52.575924+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc780b606a2a'
down_revision = 'ecdecbff60df'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('users', 'controversial')
	op.drop_column('users', 'nitter')
	op.drop_column('users', 'reddit')


def downgrade():
	# The column had no server default; one is needed only to fill existing rows
	op.add_column('users', sa.Column('reddit', sa.VARCHAR(length=15), server_default='old.reddit.com', autoincrement=False, nullable=False))
	op.alter_column('users', 'reddit', server_default=None)
	op.add_column('users', sa.Column('nitter', sa.BOOLEAN(), autoincrement=False, nullable=True))
	op.add_column('users', sa.Column('controversial', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
