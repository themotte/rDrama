"""add chat_authorized index

Revision ID: c41b790058ad
Revises: 503fd4d18a54
Create Date: 2023-08-27 12:43:34.202689+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c41b790058ad'
down_revision = '503fd4d18a54'
branch_labels = None
depends_on = None


def upgrade():
	# ### commands auto generated by Alembic - please adjust! ###
    op.create_index('chat_auth_index', 'users', ['chat_authorized'], unique=False)
    # ### end Alembic commands ###


def downgrade():
	# ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('chat_auth_index', table_name='users')
    # ### end Alembic commands ###
