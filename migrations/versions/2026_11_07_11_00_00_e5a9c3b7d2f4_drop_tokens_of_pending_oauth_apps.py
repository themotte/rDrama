"""delete the tokens of API apps awaiting approval

Revision ID: e5a9c3b7d2f4
Revises: a7c3e1f5b9d2
Create Date: 2026-11-07 11:00:00.000000+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e5a9c3b7d2f4'
down_revision = 'a7c3e1f5b9d2'
branch_labels = None
depends_on = None

# Older versions let users authorize apps that weren't approved yet; those tokens would start working once an admin approved the app.
UPGRADE_SQL = """
DELETE FROM client_auths ca
USING oauth_apps a
WHERE a.id = ca.oauth_client AND a.client_id IS NULL
"""


def upgrade():
	op.execute(UPGRADE_SQL)


def downgrade():
	# The deleted tokens aren't kept
	pass
