"""DML: populate comments.descendant_count column

Revision ID: 1f30a37b08a0
Revises: f8ba0e88ddd1
Create Date: 2023-01-03 07:59:56.599209+00:00

"""
from alembic import op
from sqlalchemy.sql.expression import func, text
from sqlalchemy.orm.session import Session
from sqlalchemy import update
from flask import g

from files.__main__ import db_session
from files.classes import Comment
from files.helpers.comments import bulk_recompute_descendant_counts


# revision identifiers, used by Alembic.
revision = '1f30a37b08a0'
down_revision = 'f8ba0e88ddd1'
branch_labels = None
depends_on = None

class g_db_set_from_alembic():
	def __enter__(self, *args, **kwargs):
		g.db = Session(bind=op.get_bind())
		self.old_db = getattr(g, 'db', None)
	def __exit__(self, *args, **kwargs):
		g.db = self.old_db


def upgrade():
	with g_db_set_from_alembic():
		bulk_recompute_descendant_counts()

def downgrade():
	with g_db_set_from_alembic():
		g.db.execute(update(Comment).values(descendant_count=0))
