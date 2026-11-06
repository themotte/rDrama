"""strip the bump sort

Revision ID: d3f1a9c2e7b4
Revises: c7e2a4f1b8d0
Create Date: 2026-11-06 12:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3f1a9c2e7b4'
down_revision = 'c7e2a4f1b8d0'
branch_labels = None
depends_on = None


def upgrade():
	op.execute("UPDATE users SET defaultsorting = 'new' WHERE defaultsorting = 'bump'")
	op.drop_column('submissions', 'bump_utc')
	op.execute("DROP FUNCTION IF EXISTS public.bump_utc(public.submissions)")


def downgrade():
	op.execute("""
		CREATE FUNCTION public.bump_utc(public.submissions) RETURNS integer
			LANGUAGE sql IMMUTABLE STRICT
			AS $_$
			SELECT CREATED_UTC
			FROM comments
			WHERE parent_submission = $1.id
			ORDER BY created_utc desc
			LIMIT 1
			$_$;
	""")
	op.add_column('submissions', sa.Column('bump_utc', sa.INTEGER(), autoincrement=False, nullable=True))
