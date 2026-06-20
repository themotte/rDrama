"""add votes-submissions foreign key on databases missing it

Revision ID: bf8588f5cd1e
Revises: 2481e3a04265
Create Date: 2026-06-20 22:02:41.816450+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf8588f5cd1e'
down_revision = '2481e3a04265'
branch_labels = None
depends_on = None


def upgrade():
	# The votes -> submissions foreign key lives in the baseline schema
	# (bootstrap/original-schema.sql, constraint "vote_submission_key") but no
	# migration ever added it. Fresh databases get it from the baseline and run
	# fine; long-lived databases (prod) predate the baseline and never got it.
	# Add it only where it's missing so we don't needlessly drop/re-validate a
	# valid constraint on databases that already have it.
	insp = sa.inspect(op.get_bind())
	has_fk = any(
		fk['referred_table'] == 'submissions'
		and fk['constrained_columns'] == ['submission_id']
		for fk in insp.get_foreign_keys('votes')
	)
	if has_fk:
		return

	# Remove orphaned votes (submission hard-deleted long ago) that would
	# violate the constraint, then add it.
	op.execute(
		"DELETE FROM votes v WHERE NOT EXISTS "
		"(SELECT 1 FROM submissions s WHERE s.id = v.submission_id)"
	)
	op.create_foreign_key(
		'vote_submission_key', 'votes', 'submissions', ['submission_id'], ['id']
	)


def downgrade():
	# Reconciliation migration: the foreign key belongs to the baseline schema,
	# so downgrading must not strip it from databases that legitimately have it.
	pass
