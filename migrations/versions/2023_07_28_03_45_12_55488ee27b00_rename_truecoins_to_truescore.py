"""rename truecoins to truescore

Revision ID: 55488ee27b00
Revises: a23fe2f1515c
Create Date: 2023-07-28 03:45:12.251007+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '55488ee27b00'
down_revision = 'a23fe2f1515c'
branch_labels = None
depends_on = None


def upgrade():
	op.alter_column('users', 'truecoins', new_column_name='truescore')


def downgrade():
	op.alter_column('users', 'truescore', new_column_name='truecoins')
