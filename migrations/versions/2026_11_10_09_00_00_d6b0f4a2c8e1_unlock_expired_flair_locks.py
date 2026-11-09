"""Clear flair locks whose time has passed

Older versions locked a user's flair until a time; the site now locks it until an admin unlocks it, holding 2147483647, and treats any value as locked. A lock left from the old kind whose time has passed is cleared, as it would have ended then.

Revision ID: d6b0f4a2c8e1
Revises: c4a8e2f6b0d5
Create Date: 2026-11-10 09:00:00.000000+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'd6b0f4a2c8e1'
down_revision = 'c4a8e2f6b0d5'
branch_labels = None
depends_on = None

UPGRADE_SQL = "UPDATE users SET flairchanged = NULL WHERE flairchanged < extract(epoch FROM now())"


def upgrade():
	op.execute(UPGRADE_SQL)


def downgrade():
	# The expired times it cleared aren't kept, and locked nothing that should have stayed locked
	pass
