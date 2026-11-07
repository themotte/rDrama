"""send every reply in a modmail thread to modmail

Revision ID: a7c3e1f5b9d2
Revises: e8b2c4d6f1a3
Create Date: 2026-11-06 18:00:00.000000+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a7c3e1f5b9d2'
down_revision = 'e8b2c4d6f1a3'
branch_labels = None
depends_on = None

# Older versions sent admins' answers in modmail to no one or to whoever they answered, and a starter's answers to the first message to no one. Replies to the site's notices (no recipient) and to comments on posts aren't in a modmail thread and stay as they are.
UPGRADE_SQL = """
UPDATE comments c SET sentto = 2
FROM comments t
WHERE t.id = c.top_comment_id
	AND t.parent_submission IS NULL AND t.sentto = 2
	AND c.id <> t.id AND c.parent_submission IS NULL
	AND c.sentto IS DISTINCT FROM 2
"""


def upgrade():
	op.execute(UPGRADE_SQL)


def downgrade():
	# The recipients it replaced aren't kept
	pass
