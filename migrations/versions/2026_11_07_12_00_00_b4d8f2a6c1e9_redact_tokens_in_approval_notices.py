"""redact access tokens from API app approval notices

Revision ID: b4d8f2a6c1e9
Revises: e5a9c3b7d2f4
Create Date: 2026-11-07 12:00:00.000000+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'b4d8f2a6c1e9'
down_revision = 'e5a9c3b7d2f4'
branch_labels = None
depends_on = None

# Older versions put the owner's access token in the notice approving their app, where every admin who can open notices could read it. The token itself stays valid and shows on the owner's apps settings page. Tokens are matched by their shape (always 128 URL-safe characters), not the notice's markup, which wordings and app names containing backticks varied.
UPGRADE_SQL = """
UPDATE comments
SET body_html = regexp_replace(body_html, '(<code>)?[A-Za-z0-9_-]{128}(</code>)?', '(shown in <a href="/settings/apps">your apps settings</a>)', 'g')
WHERE author_id = 1 AND parent_submission IS NULL
	AND body_html LIKE '%access token%' AND body_html ~ '[A-Za-z0-9_-]{128}'
"""

def upgrade():
	op.execute(UPGRADE_SQL)


def downgrade():
	# The redacted tokens aren't kept
	pass
