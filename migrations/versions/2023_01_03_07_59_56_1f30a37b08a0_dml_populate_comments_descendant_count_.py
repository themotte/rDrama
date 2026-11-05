"""DML: populate comments.descendant_count column

Revision ID: 1f30a37b08a0
Revises: f8ba0e88ddd1
Create Date: 2023-01-03 07:59:56.599209+00:00

"""
from alembic import op
from sqlalchemy.sql.expression import func, text
from sqlalchemy.orm.session import Session
from sqlalchemy import update

from files.__main__ import db_session
from files.classes import Comment


# revision identifiers, used by Alembic.
revision = '1f30a37b08a0'
down_revision = 'f8ba0e88ddd1'
branch_labels = None
depends_on = None

def upgrade():
	# Every comment's count of all comments below it, as counted when this ran (later definitions narrow it; see the comment_counts_recalc command)
	op.execute("""
		WITH RECURSIVE up(ancestor) AS (
				SELECT parent_comment_id FROM comments WHERE parent_comment_id IS NOT NULL
			UNION ALL
				SELECT c.parent_comment_id FROM comments c JOIN up ON c.id = up.ancestor WHERE c.parent_comment_id IS NOT NULL
		)
		UPDATE comments SET descendant_count = counted.n
		FROM (SELECT ancestor, count(*) AS n FROM up GROUP BY ancestor) counted
		WHERE comments.id = counted.ancestor
	""")

def downgrade():
	db: Session = Session(bind=op.get_bind())
	db.execute(update(Comment).values(descendant_count=0))
