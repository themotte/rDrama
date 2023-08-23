"""Change to datetimez table volunteer_janitor

Revision ID: 5876cd139e31
Revises: d08833c2adc7
Create Date: 2023-08-23 02:02:38.487237+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql.functions import now


# revision identifiers, used by Alembic.
revision = '5876cd139e31'
down_revision = 'd08833c2adc7'
branch_labels = None
depends_on = None

table_name = 'volunteer_janitor'
from_column = 'recorded_utc'
to_column = 'recorded_datetimez'

def upgrade():
	op.alter_column(table_name, from_column, new_column_name=to_column, type_=sa.DateTime(timezone=True), server_default=now())


def downgrade():
	op.alter_column(table_name, to_column, new_column_name=from_column, type_=sa.DateTime())
