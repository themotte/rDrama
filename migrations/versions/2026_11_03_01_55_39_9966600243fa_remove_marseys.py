"""remove marseys

Revision ID: 9966600243fa
Revises: 479692d3038e
Create Date: 2026-11-03 01:55:39.831517+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9966600243fa'
down_revision = '479692d3038e'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_index('marseys_idx', table_name='marseys')
	op.drop_index('marseys_idx2', table_name='marseys')
	op.drop_index('marseys_idx3', table_name='marseys')
	op.drop_table('marseys')


def downgrade():
	op.create_table('marseys',
	sa.Column('name', sa.VARCHAR(length=30), autoincrement=False, nullable=False),
	sa.Column('author_id', sa.INTEGER(), autoincrement=False, nullable=False),
	sa.Column('tags', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
	sa.Column('count', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
	sa.ForeignKeyConstraint(['author_id'], ['users.id'], name='marsey_author_fkey'),
	sa.PrimaryKeyConstraint('name', name='marseys_pkey')
	)
	op.create_index('marseys_idx3', 'marseys', [sa.literal_column('count DESC')], unique=False)
	op.create_index('marseys_idx2', 'marseys', ['author_id'], unique=False)
	op.create_index('marseys_idx', 'marseys', ['name'], unique=False)
