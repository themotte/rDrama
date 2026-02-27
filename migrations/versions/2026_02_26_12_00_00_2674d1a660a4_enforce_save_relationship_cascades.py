"""Enforce save relationship cascades

Add ON DELETE CASCADE to save_relationship and comment_save_relationship
foreign keys so that saves are automatically cleaned up when the referenced
user, submission, or comment is deleted.

Fixes https://github.com/themotte/rDrama/issues/468

Revision ID: 2674d1a660a4
Revises: 2481e3a04265
Create Date: 2026-02-26 12:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2674d1a660a4'
down_revision = '2481e3a04265'
branch_labels = None
depends_on = None


def upgrade():
	# Drop existing FK constraints (no cascade) and recreate with ON DELETE CASCADE

	# save_relationship: submission_id -> submissions.id
	op.drop_constraint('save_relationship_submission_fkey', 'save_relationship', type_='foreignkey')
	op.create_foreign_key(
		'save_relationship_submission_fkey', 'save_relationship',
		'submissions', ['submission_id'], ['id'], ondelete='CASCADE'
	)

	# save_relationship: user_id -> users.id
	op.drop_constraint('save_relationship_user_fkey', 'save_relationship', type_='foreignkey')
	op.create_foreign_key(
		'save_relationship_user_fkey', 'save_relationship',
		'users', ['user_id'], ['id'], ondelete='CASCADE'
	)

	# comment_save_relationship: comment_id -> comments.id
	op.drop_constraint('comment_save_relationship_comment_fkey', 'comment_save_relationship', type_='foreignkey')
	op.create_foreign_key(
		'comment_save_relationship_comment_fkey', 'comment_save_relationship',
		'comments', ['comment_id'], ['id'], ondelete='CASCADE'
	)

	# comment_save_relationship: user_id -> users.id
	op.drop_constraint('comment_save_relationship_user_fkey', 'comment_save_relationship', type_='foreignkey')
	op.create_foreign_key(
		'comment_save_relationship_user_fkey', 'comment_save_relationship',
		'users', ['user_id'], ['id'], ondelete='CASCADE'
	)


def downgrade():
	# Revert to original FK constraints without ON DELETE CASCADE

	# comment_save_relationship: user_id -> users.id
	op.drop_constraint('comment_save_relationship_user_fkey', 'comment_save_relationship', type_='foreignkey')
	op.create_foreign_key(
		'comment_save_relationship_user_fkey', 'comment_save_relationship',
		'users', ['user_id'], ['id']
	)

	# comment_save_relationship: comment_id -> comments.id
	op.drop_constraint('comment_save_relationship_comment_fkey', 'comment_save_relationship', type_='foreignkey')
	op.create_foreign_key(
		'comment_save_relationship_comment_fkey', 'comment_save_relationship',
		'comments', ['comment_id'], ['id']
	)

	# save_relationship: user_id -> users.id
	op.drop_constraint('save_relationship_user_fkey', 'save_relationship', type_='foreignkey')
	op.create_foreign_key(
		'save_relationship_user_fkey', 'save_relationship',
		'users', ['user_id'], ['id']
	)

	# save_relationship: submission_id -> submissions.id
	op.drop_constraint('save_relationship_submission_fkey', 'save_relationship', type_='foreignkey')
	op.create_foreign_key(
		'save_relationship_submission_fkey', 'save_relationship',
		'submissions', ['submission_id'], ['id']
	)
