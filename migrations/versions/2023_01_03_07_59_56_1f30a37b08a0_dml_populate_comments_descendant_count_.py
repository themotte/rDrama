"""DML: populate comments.descendant_count column

Revision ID: 1f30a37b08a0
Revises: f8ba0e88ddd1
Create Date: 2023-01-03 07:59:56.599209+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql.expression import func

from files.__main__ import db_session
from files.classes import Comment

# revision identifiers, used by Alembic.
revision = '1f30a37b08a0'
down_revision = 'f8ba0e88ddd1'
branch_labels = None
depends_on = None

def upgrade():
	db = db_session()

	max_level = db.query(func.max(Comment.level)).scalar()
	for level in range(max_level, 0, -1):
		db.execute('''
			WITH "descendant_counts" as (
				SELECT
					"parent_comments"."id",
					COALESCE(SUM(1 + "child_comments"."descendant_count"), 0) as "descendant_count"
				FROM "comments" as "parent_comments"
					LEFT JOIN "comments" AS "child_comments" ON "child_comments"."parent_comment_id" = "parent_comments"."id"
				GROUP BY "parent_comments"."id"
			)
			UPDATE "comments"
			SET "descendant_count" = "descendant_counts"."descendant_count"
			FROM "descendant_counts"
			WHERE "comments"."id" = "descendant_counts"."id"
		''', {"level": level})
	db.commit()


def downgrade():
	db = db_session()
	db.query(Comment).update({'descendant_count': 0})
