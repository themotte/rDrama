"""recalculate all volunteer janitor ephemeral data

Revision ID: 6403c9151c12
Revises: b2373d7b1b84
Create Date: 2023-04-22 11:33:50.049868+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm.session import Session

from files.commands.volunteer_janitor_recalc import volunteer_janitor_recalc_all_comments

# revision identifiers, used by Alembic.
revision = '6403c9151c12'
down_revision = 'b2373d7b1b84'
branch_labels = None
depends_on = None


def upgrade():
    # this is now disabled because this code is no longer compatible with this version of the DB
    #volunteer_janitor_recalc_all_comments(Session(bind=op.get_bind()))
    pass


def downgrade():
       pass
