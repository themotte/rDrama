"""rejigger of the mod/report comment/post state flags

Revision ID: ea282d7c711c
Revises: 4bb8194c8ac0
Create Date: 2023-06-25 07:09:36.333792+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea282d7c711c'
down_revision = '4bb8194c8ac0'
branch_labels = None
depends_on = None


def upgrade():
	state_mod_enum = sa.Enum('VISIBLE', 'FILTERED', 'REMOVED', name='statemod', create_type=False)
	state_report_enum = sa.Enum('UNREPORTED', 'RESOLVED', 'REPORTED', 'IGNORED', name='statereport', create_type=False)

	state_mod_enum.create(op.get_bind(), checkfirst=True)
	state_report_enum.create(op.get_bind(), checkfirst=True)

	op.add_column('comments', sa.Column('state_mod', state_mod_enum, nullable=True))
	op.add_column('comments', sa.Column('state_mod_set_by', sa.String(), nullable=True))
	op.add_column('comments', sa.Column('state_report', state_report_enum, nullable=True))
	op.drop_index('fki_comment_approver_fkey', table_name='comments')
	op.drop_constraint('comment_approver_fkey', 'comments', type_='foreignkey')

	# If `is_banned`, set `state_mod` to the `REMOVED` enum
	# otherwise, if `filter_state` is `FILTERED`, set `state_mod` to the `FILTERED` enum
	# otherwise, set `state_mod` to the `VISIBLE` enum
	op.execute("""
		UPDATE comments 
		SET state_mod = CASE 
			WHEN is_banned THEN 'REMOVED'::statemod
			WHEN filter_state = 'FILTERED' THEN 'FILTERED'::statemod
			ELSE 'VISIBLE'::statemod
		END
	""")

	# if `state_mod` is `REMOVED`, set `state_mod_set_by` to `ban_reason`
	# otherwise, if `state_mod` is `VISIBLE`, set `state_mod_set_by` to the `username` of the `users` table, indexed by `is_approved == users.id`
	op.execute("""
		UPDATE comments
		SET state_mod_set_by = CASE
			WHEN state_mod = 'REMOVED' THEN ban_reason
			WHEN state_mod = 'VISIBLE' THEN (SELECT username FROM users WHERE id = is_approved)
		END
	""")

	# if `filter_state` is `IGNORED`, set `state_report` to the `IGNORED` enum
	# otherwise, if `filter_state` is `REPORTED`, set `state_report` to the `REPORTED` enum
	# otherwise, if `state_mod_set_by` is non-NULL, set `state_report` to the `RESOLVED` enum
	# otherwise, set `state_report` to the `UNREPORTED` enum
	op.execute("""
		UPDATE comments
		SET state_report = CASE
			WHEN filter_state = 'IGNORED' THEN 'IGNORED'::statereport
			WHEN filter_state = 'REPORTED' THEN 'REPORTED'::statereport
			WHEN state_mod_set_by IS NOT NULL THEN 'RESOLVED'::statereport
			ELSE 'UNREPORTED'::statereport
		END
	""")

	op.alter_column('comments', 'state_mod', nullable=False)
	op.alter_column('comments', 'state_report', nullable=False)

	op.drop_column('comments', 'is_banned')
	op.drop_column('comments', 'ban_reason')
	op.drop_column('comments', 'is_approved')
	op.drop_column('comments', 'filter_state')



	op.add_column('submissions', sa.Column('state_mod', state_mod_enum, nullable=True))
	op.add_column('submissions', sa.Column('state_mod_set_by', sa.String(), nullable=True))
	op.add_column('submissions', sa.Column('state_report', state_report_enum, nullable=True))
	op.drop_index('fki_submissions_approver_fkey', table_name='submissions')
	op.drop_index('submission_isbanned_idx', table_name='submissions')
	op.drop_index('subimssion_binary_group_idx', table_name='submissions')
	op.create_index('subimssion_binary_group_idx', 'submissions', ['state_mod', 'state_user_deleted_utc', 'over_18'], unique=False)
	op.drop_index('submission_new_sort_idx', table_name='submissions')
	op.create_index('submission_new_sort_idx', 'submissions', ['state_mod', 'state_user_deleted_utc', sa.text('created_utc DESC'), 'over_18'], unique=False)
	op.create_index('submission_state_mod_idx', 'submissions', ['state_mod'], unique=False)
	op.drop_constraint('submissions_approver_fkey', 'submissions', type_='foreignkey')

	# If `is_banned`, set `state_mod` to the `REMOVED` enum
	# otherwise, if `filter_state` is `FILTERED`, set `state_mod` to the `FILTERED` enum
	# otherwise, set `state_mod` to the `VISIBLE` enum
	op.execute("""
		UPDATE submissions 
		SET state_mod = CASE 
			WHEN is_banned THEN 'REMOVED'::statemod
			WHEN filter_state = 'FILTERED' THEN 'FILTERED'::statemod
			ELSE 'VISIBLE'::statemod
		END
	""")

	# if `state_mod` is `REMOVED`, set `state_mod_set_by` to `ban_reason`
	# otherwise, if `state_mod` is `VISIBLE`, set `state_mod_set_by` to the `username` of the `users` table, indexed by `is_approved == users.id`
	op.execute("""
		UPDATE submissions
		SET state_mod_set_by = CASE
			WHEN state_mod = 'REMOVED' THEN ban_reason
			WHEN state_mod = 'VISIBLE' THEN (SELECT username FROM users WHERE id = is_approved)
		END
	""")

	# if `filter_state` is `IGNORED`, set `state_report` to the `IGNORED` enum
	# otherwise, if `filter_state` is `REPORTED`, set `state_report` to the `REPORTED` enum
	# otherwise, if `state_mod_set_by` is non-NULL, set `state_report` to the `RESOLVED` enum
	# otherwise, set `state_report` to the `UNREPORTED` enum
	op.execute("""
		UPDATE submissions
		SET state_report = CASE
			WHEN filter_state = 'IGNORED' THEN 'IGNORED'::statereport
			WHEN filter_state = 'REPORTED' THEN 'REPORTED'::statereport
			WHEN state_mod_set_by IS NOT NULL THEN 'RESOLVED'::statereport
			ELSE 'UNREPORTED'::statereport
		END
	""")

	op.alter_column('submissions', 'state_mod', nullable=False)
	op.alter_column('submissions', 'state_report', nullable=False)

	op.drop_column('submissions', 'is_banned')
	op.drop_column('submissions', 'ban_reason')
	op.drop_column('submissions', 'is_approved')
	op.drop_column('submissions', 'filter_state')


def downgrade():
	op.add_column('comments', sa.Column('filter_state', sa.VARCHAR(length=40), autoincrement=False, nullable=True))
	op.add_column('comments', sa.Column('is_approved', sa.INTEGER(), autoincrement=False, nullable=True))
	op.add_column('comments', sa.Column('ban_reason', sa.VARCHAR(length=25), autoincrement=False, nullable=True))
	op.add_column('comments', sa.Column('is_banned', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=True))
	op.create_foreign_key('comment_approver_fkey', 'comments', 'users', ['is_approved'], ['id'])
	op.create_index('fki_comment_approver_fkey', 'comments', ['is_approved'], unique=False)

	op.execute("""
		UPDATE comments 
		SET is_banned = CASE 
			WHEN state_mod = 'REMOVED' THEN TRUE
			ELSE FALSE
		END
	""")

	op.execute("""
		UPDATE comments 
		SET is_approved = (SELECT id FROM users WHERE username = state_mod_set_by)
		WHERE state_mod = 'VISIBLE' AND (state_report = 'RESOLVED' OR state_report = 'IGNORED')
	""")

	op.execute("""
		UPDATE comments
		SET ban_reason = CASE
			WHEN state_mod = 'REMOVED' THEN state_mod_set_by
			ELSE NULL
		END
	""")

	op.execute("""
		UPDATE comments
		SET filter_state = CASE
			WHEN state_report = 'IGNORED' THEN 'IGNORED'
			WHEN state_report = 'REPORTED' THEN 'REPORTED'
			WHEN state_mod = 'FILTERED' THEN 'FILTERED'
			ELSE NULL
		END
	""")

	op.alter_column('comments', sa.Column('filter_state', sa.VARCHAR(length=40), autoincrement=False, nullable=True))
	op.alter_column('comments', sa.Column('is_banned', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=True))

	op.drop_column('comments', 'state_report')
	op.drop_column('comments', 'state_mod_set_by')
	op.drop_column('comments', 'state_mod')
	
	op.add_column('submissions', sa.Column('filter_state', sa.VARCHAR(length=40), autoincrement=False, nullable=True))
	op.add_column('submissions', sa.Column('is_approved', sa.INTEGER(), autoincrement=False, nullable=True))
	op.add_column('submissions', sa.Column('ban_reason', sa.VARCHAR(length=25), autoincrement=False, nullable=True))
	op.add_column('submissions', sa.Column('is_banned', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=True))
	op.create_foreign_key('submissions_approver_fkey', 'submissions', 'users', ['is_approved'], ['id'])
	op.drop_index('submission_state_mod_idx', table_name='submissions')
	op.drop_index('submission_new_sort_idx', table_name='submissions')
	op.create_index('submission_new_sort_idx', 'submissions', ['is_banned', 'state_user_deleted_utc', 'created_utc', 'over_18'], unique=False)
	op.drop_index('subimssion_binary_group_idx', table_name='submissions')
	op.create_index('subimssion_binary_group_idx', 'submissions', ['is_banned', 'state_user_deleted_utc', 'over_18'], unique=False)
	op.create_index('submission_isbanned_idx', 'submissions', ['is_banned'], unique=False)
	op.create_index('fki_submissions_approver_fkey', 'submissions', ['is_approved'], unique=False)

	op.execute("""
		UPDATE submissions 
		SET is_banned = CASE 
			WHEN state_mod = 'REMOVED' THEN TRUE
			ELSE FALSE
		END
	""")

	op.execute("""
		UPDATE submissions 
		SET is_approved = (SELECT id FROM users WHERE username = state_mod_set_by)
		WHERE state_mod = 'VISIBLE' AND (state_report = 'RESOLVED' OR state_report = 'IGNORED')
	""")

	op.execute("""
		UPDATE submissions
		SET ban_reason = CASE
			WHEN state_mod = 'REMOVED' THEN state_mod_set_by
			ELSE NULL
		END
	""")

	op.execute("""
		UPDATE submissions
		SET filter_state = CASE
			WHEN state_report = 'IGNORED' THEN 'IGNORED'
			WHEN state_report = 'REPORTED' THEN 'REPORTED'
			WHEN state_mod = 'FILTERED' THEN 'FILTERED'
			ELSE NULL
		END
	""")

	op.alter_column('submissions', sa.Column('filter_state', sa.VARCHAR(length=40), autoincrement=False, nullable=True))
	op.alter_column('submissions', sa.Column('is_banned', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=True))

	op.drop_column('submissions', 'state_report')
	op.drop_column('submissions', 'state_mod_set_by')
	op.drop_column('submissions', 'state_mod')

