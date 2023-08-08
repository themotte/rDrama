"""excise country club

Revision ID: d08833c2adc7
Revises: 85dad82a4a67
Create Date: 2023-08-08 14:36:38.797624+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd08833c2adc7'
down_revision = '85dad82a4a67'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('submissions', 'club')
	op.drop_column('users', 'club_allowed')


def downgrade():
	op.add_column('users', sa.Column('club_allowed', sa.BOOLEAN(), autoincrement=False, nullable=True))
	op.add_column('submissions', sa.Column('club', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
	op.add_column('commentvotes', sa.Column('created_utc', sa.INTEGER(), autoincrement=False, nullable=False))
