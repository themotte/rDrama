"""Add filter_state to comments

Revision ID: c5bbdae9a233
Revises: dd9a3c418274
Create Date: 2022-06-07 03:30:19.727632+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5bbdae9a233'
down_revision = 'dd9a3c418274'
branch_labels = None
depends_on = None


def upgrade():
	op.add_column('comments', sa.Column('filter_state', sa.String(40), nullable=True))
	op.execute("UPDATE comments SET filter_state = 'normal';")
	op.alter_column('comments', 'filter_state', nullable=False)
	op.drop_constraint('commentflags_pkey', 'commentflags')
	op.add_column('commentflags', sa.Column('id', sa.Integer, nullable=False, primary_key=True, autoincrement=True))


def downgrade():
	op.drop_column('comments', 'filter_state')
	op.drop_column('commentflags', 'id')
	op.create_primary_key('commentflags_pkey', 'commentflags', ['post_id', 'user_id'])
