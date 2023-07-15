"""Move 'deleted_utc' into 'state_user_deleted_utc'.

Revision ID: 8337558f4f36
Revises: 6403c9151c12
Create Date: 2023-06-11 09:09:00.235602+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8337558f4f36'
down_revision = '6403c9151c12'
branch_labels = None
depends_on = None


def upgrade():
	op.add_column('comments', sa.Column('state_user_deleted_utc', sa.DateTime(timezone=True), nullable=True))
	op.add_column('submissions', sa.Column('state_user_deleted_utc', sa.DateTime(timezone=True), nullable=True))

	op.drop_index('subimssion_binary_group_idx', table_name='submissions')
	op.drop_index('submission_isdeleted_idx', table_name='submissions')
	op.drop_index('submission_new_sort_idx', table_name='submissions')

	op.execute("""
		UPDATE comments 
		SET state_user_deleted_utc = 
			CASE 
				WHEN deleted_utc > 0 THEN 
					(timestamp 'epoch' + deleted_utc * interval '1 second') at time zone 'utc' 
				ELSE NULL 
			END
	""")

	op.execute("""
		UPDATE submissions 
		SET state_user_deleted_utc = 
			CASE 
				WHEN deleted_utc > 0 THEN 
					(timestamp 'epoch' + deleted_utc * interval '1 second') at time zone 'utc' 
				ELSE NULL 
			END
	""")

	op.drop_column('comments', 'deleted_utc')
	op.drop_column('submissions', 'deleted_utc')

	op.create_index('subimssion_binary_group_idx', 'submissions', ['is_banned', 'state_user_deleted_utc', 'over_18'], unique=False)
	op.create_index('submission_isdeleted_idx', 'submissions', ['state_user_deleted_utc'], unique=False)
	op.create_index('submission_new_sort_idx', 'submissions', ['is_banned', 'state_user_deleted_utc', sa.text('created_utc DESC'), 'over_18'], unique=False)




def downgrade():
	op.add_column('comments', sa.Column('deleted_utc', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True))
	op.add_column('submissions', sa.Column('deleted_utc', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True))

	op.drop_index('submission_new_sort_idx', table_name='submissions')
	op.drop_index('submission_isdeleted_idx', table_name='submissions')
	op.drop_index('subimssion_binary_group_idx', table_name='submissions')

	op.execute("""
		UPDATE comments 
		SET deleted_utc = 
			COALESCE(
				EXTRACT(EPOCH FROM state_user_deleted_utc)::integer,
				0
			)
		""")
	
	op.execute("""
		UPDATE submissions 
		SET deleted_utc = 
			COALESCE(
				EXTRACT(EPOCH FROM state_user_deleted_utc)::integer,
				0
			)
		""")

	op.alter_column('comments', 'deleted_utc', nullable=False)
	op.alter_column('submissions', 'deleted_utc', nullable=False)

	op.drop_column('comments', 'state_user_deleted_utc')
	op.drop_column('submissions', 'state_user_deleted_utc')

	op.create_index('submission_new_sort_idx', 'submissions', ['is_banned', 'deleted_utc', 'created_utc', 'over_18'], unique=False)
	op.create_index('submission_isdeleted_idx', 'submissions', ['deleted_utc'], unique=False)
	op.create_index('subimssion_binary_group_idx', 'submissions', ['is_banned', 'deleted_utc', 'over_18'], unique=False)

