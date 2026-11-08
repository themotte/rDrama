"""record when each task's schedule last changed

Revision ID: e7b3d9f1a5c8
Revises: d2f6b8e4a1c7
Create Date: 2026-11-08 20:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7b3d9f1a5c8'
down_revision = 'd2f6b8e4a1c7'
branch_labels = None
depends_on = None

# Existing schedules count as set when their task was created
BACKFILL_SQL = "UPDATE tasks_repeatable SET schedule_changed_utc = to_timestamp(created_utc) AT TIME ZONE 'UTC'"


def upgrade():
	op.add_column('tasks_repeatable', sa.Column('schedule_changed_utc', sa.DateTime(), nullable=True))
	op.execute(BACKFILL_SQL)
	op.alter_column('tasks_repeatable', 'schedule_changed_utc', nullable=False)


def downgrade():
	op.drop_column('tasks_repeatable', 'schedule_changed_utc')
