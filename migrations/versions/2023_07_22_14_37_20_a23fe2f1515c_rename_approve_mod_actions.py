"""Rename approve mod actions

Revision ID: a23fe2f1515c
Revises: 7ae4658467d7
Create Date: 2023-07-22 14:37:20.485816+00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a23fe2f1515c'
down_revision = '7ae4658467d7'
branch_labels = None
depends_on = None


def upgrade():
	op.execute("UPDATE modactions SET kind='approve_post' WHERE kind='unremove_post';")
	op.execute("UPDATE modactions SET kind='approve_comment' WHERE kind='unremove_comment';")


def downgrade():
	op.execute("UPDATE modactions SET kind='unremove_post' WHERE kind='approve_post';")
	op.execute("UPDATE modactions SET kind='unremove_comment' WHERE kind='approve_comment';")
