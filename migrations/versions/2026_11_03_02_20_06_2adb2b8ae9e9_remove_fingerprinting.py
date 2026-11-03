"""remove fingerprinting

Revision ID: 2adb2b8ae9e9
Revises: 9966600243fa
Create Date: 2026-11-03 02:20:06.262089+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2adb2b8ae9e9'
down_revision = '9966600243fa'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('users', 'fp')


def downgrade():
	op.add_column('users', sa.Column('fp', sa.VARCHAR(length=21), autoincrement=False, nullable=True))
