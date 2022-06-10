"""Add filter_state and update flags schema

Revision ID: dd9a3c418274
Revises: 16d6335dd9a3
Create Date: 2022-05-22 21:59:30.104333+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd9a3c418274'
down_revision = '16d6335dd9a3'
branch_labels = None
depends_on = None


def upgrade():
	op.add_column('submissions', sa.Column('filter_state', sa.String(40), nullable=True))
	op.execute("UPDATE submissions SET filter_state = 'normal';")
	op.alter_column('submissions', 'filter_state', nullable=False)
	op.drop_constraint('flags_pkey', 'flags')
	op.execute('alter table flags add column id serial primary key')


def downgrade():
	op.drop_column('submissions', 'filter_state')
	op.drop_column('flags', 'id')
	op.create_primary_key('flags_id_pk', 'flags', ['post_id', 'user_id'])
