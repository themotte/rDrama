"""drop vote app ids

Revision ID: c7e2a4f1b8d0
Revises: b4d6e1a2c9f3
Create Date: 2026-11-05 12:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7e2a4f1b8d0'
down_revision = 'b4d6e1a2c9f3'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('votes', 'app_id')
	op.drop_column('commentvotes', 'app_id')


def downgrade():
	op.add_column('commentvotes', sa.Column('app_id', sa.INTEGER(), autoincrement=False, nullable=True))
	op.create_foreign_key('commentvotes_app_id_fkey', 'commentvotes', 'oauth_apps', ['app_id'], ['id'])
	op.add_column('votes', sa.Column('app_id', sa.INTEGER(), autoincrement=False, nullable=True))
	op.create_foreign_key('votes_app_id_fkey', 'votes', 'oauth_apps', ['app_id'], ['id'])
