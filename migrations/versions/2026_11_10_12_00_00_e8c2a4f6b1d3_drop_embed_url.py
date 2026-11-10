"""Drop the post embed columns: submissions.embed_url, tasks_repeatable_scheduled_submissions.embed_url

The site no longer makes YouTube or Twitter embeds, and its content security policy already kept browsers from showing the stored ones. Downgrading adds the columns back empty.

Revision ID: e8c2a4f6b1d3
Revises: d6b0f4a2c8e1
Create Date: 2026-11-10 12:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8c2a4f6b1d3'
down_revision = 'd6b0f4a2c8e1'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_column('submissions', 'embed_url')
	op.drop_column('tasks_repeatable_scheduled_submissions', 'embed_url')


def downgrade():
	op.add_column('tasks_repeatable_scheduled_submissions', sa.Column('embed_url', sa.String(), nullable=True))
	op.add_column('submissions', sa.Column('embed_url', sa.String(length=1500), nullable=True))
