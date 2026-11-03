"""recount users' post counts without drafts

Revision ID: 5f3c2a9d7e41
Revises: dc780b606a2a
Create Date: 2026-11-03 12:00:00.000000+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '5f3c2a9d7e41'
down_revision = 'dc780b606a2a'
branch_labels = None
depends_on = None


def upgrade():
	# Counts were only ever set when posting, so deletions and removals left them stale, and drafts were included
	op.execute("""
		UPDATE users SET post_count = (
			SELECT count(*) FROM submissions
			WHERE submissions.author_id = users.id
				AND submissions.state_mod = 'VISIBLE'
				AND submissions.state_user_deleted_utc IS NULL
				AND NOT submissions.private
		)
	""")


def downgrade():
	# The counts as they were can't be recovered, and the corrected ones are valid under the old code too
	pass
