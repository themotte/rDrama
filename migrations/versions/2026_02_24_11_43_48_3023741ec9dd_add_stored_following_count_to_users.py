"""add stored_following_count to users

Revision ID: 3023741ec9dd
Revises: c5428295e344
Create Date: 2026-02-24 11:43:48.182508+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3023741ec9dd'
down_revision = 'c5428295e344'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stored_following_count', sa.Integer(), server_default='0', nullable=False))

    op.execute("""
        UPDATE users SET stored_following_count = (
            SELECT COUNT(*) FROM follows WHERE follows.user_id = users.id
        )
    """)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('stored_following_count')
