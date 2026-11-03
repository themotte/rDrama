"""remove patrons and profile views

Revision ID: 479692d3038e
Revises: b29c2a442079
Create Date: 2026-11-03 01:45:15.423778+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '479692d3038e'
down_revision = 'b29c2a442079'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_index('fki_view_viewer_fkey', table_name='viewers')
	op.drop_table('viewers')

	op.drop_column('users', 'patron')
	op.drop_column('users', 'patron_utc')


def downgrade():
	op.add_column('users', sa.Column('patron_utc', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
	op.add_column('users', sa.Column('patron', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))

	op.create_table('viewers',
	sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
	sa.Column('viewer_id', sa.INTEGER(), autoincrement=False, nullable=False),
	sa.Column('last_view_datetimez', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
	sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='view_user_fkey'),
	sa.ForeignKeyConstraint(['viewer_id'], ['users.id'], name='view_viewer_fkey'),
	sa.PrimaryKeyConstraint('user_id', 'viewer_id', name='viewers_pkey')
	)
	op.create_index('fki_view_viewer_fkey', 'viewers', ['viewer_id'], unique=False)
