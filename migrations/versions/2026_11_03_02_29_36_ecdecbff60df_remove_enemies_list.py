"""remove enemies list

Revision ID: ecdecbff60df
Revises: 2adb2b8ae9e9
Create Date: 2026-11-03 02:29:36.911215+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ecdecbff60df'
down_revision = '2adb2b8ae9e9'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('users', 'enemies_html')
	op.drop_column('users', 'enemies')


def downgrade():
	op.add_column('users', sa.Column('enemies', sa.VARCHAR(length=500), autoincrement=False, nullable=True))
	op.add_column('users', sa.Column('enemies_html', sa.VARCHAR(length=2000), autoincrement=False, nullable=True))
