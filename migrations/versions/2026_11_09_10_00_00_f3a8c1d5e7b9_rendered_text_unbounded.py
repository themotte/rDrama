"""Columns holding rendered text are unbounded

Text limits count what users type; how long its rendering comes out must not decide whether it's taken. Downgrading cuts longer values to the old lengths.

Revision ID: f3a8c1d5e7b9
Revises: e7b3d9f1a5c8
Create Date: 2026-11-09 10:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a8c1d5e7b9'
down_revision = 'e7b3d9f1a5c8'
branch_labels = None
depends_on = None

COLUMNS = [
	("commentflags", "reason", 350),
	("flags", "reason", 350),
	("modactions", "_note", 256),
	("submissions", "flair", 350),
	("submissions", "title_html", 1500),
	("users", "bio_html", 10000),
	("users", "ban_reason", 256),
	("users", "customtitle", 1000),
	("users", "friends_html", 2000),
]


def upgrade():
	for table, column, length in COLUMNS:
		op.alter_column(table, column, type_=sa.String(), existing_type=sa.String(length))
	# A default of NULL is no default; once the type changes, a dump leaves it out
	op.alter_column("modactions", "_note", server_default=None, existing_type=sa.String())


def downgrade():
	for table, column, length in COLUMNS:
		op.execute(f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE varchar({length}) USING left("{column}", {length})')
	op.execute('ALTER TABLE modactions ALTER COLUMN "_note" SET DEFAULT NULL::character varying')
