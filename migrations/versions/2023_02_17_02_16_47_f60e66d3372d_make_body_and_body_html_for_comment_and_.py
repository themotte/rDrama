
"""make body and body_html for comment and submission infinite

Revision ID: f60e66d3372d
Revises: ba8a214736eb
Create Date: 2023-02-17 02:16:47.436983+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f60e66d3372d'
down_revision = 'ba8a214736eb'
branch_labels = None
depends_on = None


def upgrade():
	# ### commands adjusted to fix automigration ### #
	op.alter_column('submissions', 'body', type_=sa.TEXT)
	op.alter_column('submissions', 'body_html', _type=sa.TEXT)
	op.alter_column('comments', 'body', _type=sa.TEXT)
	op.alter_column('comments', 'body_html', _type=sa.TEXT, nullable=False)
	# ### end Alembic commands ###


def downgrade():
	# ### commands adjusted to fix automigration ### #
	op.alter_column('submissions', 'body', _type=sa.VARCHAR(length=40000))
	op.alter_column('submissions', 'body_html', _type=sa.VARCHAR(length=40000))
	op.alter_column('comments', 'body', _type=sa.VARCHAR(length=40000))
	op.alter_column('comments', 'body_html', _type=sa.VARCHAR(length=40000), nullable=True)
	# ### end Alembic commands ###
