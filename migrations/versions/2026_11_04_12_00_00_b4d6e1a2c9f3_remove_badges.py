"""remove badges

Revision ID: b4d6e1a2c9f3
Revises: 5f3c2a9d7e41
Create Date: 2026-11-04 12:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4d6e1a2c9f3'
down_revision = '5f3c2a9d7e41'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_index('badges_badge_id_idx', table_name='badges')
	op.drop_table('badges')
	op.drop_table('badge_defs')


def downgrade():
	op.create_table('badge_defs',
	sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
	sa.Column('name', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
	sa.Column('description', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
	sa.PrimaryKeyConstraint('id', name='badge_defs_pkey'),
	sa.UniqueConstraint('name', name='badge_def_name_unique')
	)
	op.create_table('badges',
	sa.Column('badge_id', sa.INTEGER(), autoincrement=False, nullable=False),
	sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
	sa.Column('description', sa.VARCHAR(length=256), autoincrement=False, nullable=True),
	sa.Column('url', sa.VARCHAR(length=256), autoincrement=False, nullable=True),
	sa.ForeignKeyConstraint(['badge_id'], ['badge_defs.id'], name='badges_badge_id_fkey'),
	sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='badges_user_id_fkey'),
	sa.PrimaryKeyConstraint('user_id', 'badge_id', name='badges_pkey')
	)
	op.create_index('badges_badge_id_idx', 'badges', ['badge_id'], unique=False)
