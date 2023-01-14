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
from files.helpers.comments import bulk_recompute_descendant_counts


# revision identifiers, used by Alembic.
revision = '1f30a37b08a0'
down_revision = 'f8ba0e88ddd1'
branch_labels = None
depends_on = None

def upgrade():
	db =Session(bind=op.get_bind())
	bulk_recompute_descendant_counts(lambda q: q, db)

def downgrade():
	db =Session(bind=op.get_bind())
	db.execute(update(Comment).values(descendant_count=0))
