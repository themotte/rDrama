"""remove dead user columns

Revision ID: b29c2a442079
Revises: f00c19ac858c
Create Date: 2026-11-03 01:35:08.379101+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b29c2a442079'
down_revision = 'f00c19ac858c'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('users', 'winnings')
	op.drop_column('users', 'slurreplacer')
	op.drop_column('users', 'agendaposter')


def downgrade():
	op.add_column('users', sa.Column('agendaposter', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
	op.add_column('users', sa.Column('slurreplacer', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False))
	op.add_column('users', sa.Column('winnings', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
