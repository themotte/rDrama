"""Drop columns nothing uses: comments.is_pinned_utc, tasks_repeatable_runs.manual, tasks_repeatable_scheduled_submissions.is_bot

Nothing wrote comments.is_pinned_utc, and the other two were always false. Downgrading adds them back empty or false.

Revision ID: c4a8e2f6b0d5
Revises: f3a8c1d5e7b9
Create Date: 2026-11-09 17:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4a8e2f6b0d5'
down_revision = 'f3a8c1d5e7b9'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('comments', 'is_pinned_utc')
	op.drop_column('tasks_repeatable_runs', 'manual')
	op.drop_column('tasks_repeatable_scheduled_submissions', 'is_bot')


def downgrade():
	op.add_column('tasks_repeatable_scheduled_submissions', sa.Column('is_bot', sa.Boolean(), server_default=sa.false(), nullable=False))
	op.alter_column('tasks_repeatable_scheduled_submissions', 'is_bot', server_default=None)
	op.add_column('tasks_repeatable_runs', sa.Column('manual', sa.Boolean(), server_default=sa.false(), nullable=False))
	op.alter_column('tasks_repeatable_runs', 'manual', server_default=None)
	op.add_column('comments', sa.Column('is_pinned_utc', sa.Integer(), nullable=True))
