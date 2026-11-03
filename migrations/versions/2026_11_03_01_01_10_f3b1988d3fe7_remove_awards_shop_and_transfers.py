"""remove awards, shop and transfers

Revision ID: f3b1988d3fe7
Revises: bf8588f5cd1e
Create Date: 2026-11-03 01:01:10.845347+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3b1988d3fe7'
down_revision = 'bf8588f5cd1e'
branch_labels = None
depends_on = None


def upgrade():
	op.drop_index('award_comment_idx', table_name='award_relationships')
	op.drop_index('award_post_idx', table_name='award_relationships')
	op.drop_index('award_user_idx', table_name='award_relationships')
	op.drop_table('award_relationships')

	op.drop_column('users', 'received_award_count')
	op.drop_column('users', 'coins_spent')
	op.drop_column('users', 'lootboxes_bought')

	op.execute("DELETE FROM modactions WHERE kind = 'grant_awards'")


def downgrade():
	op.add_column('users', sa.Column('lootboxes_bought', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
	op.add_column('users', sa.Column('coins_spent', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
	op.add_column('users', sa.Column('received_award_count', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))

	op.create_table('award_relationships',
	sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
	sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
	sa.Column('submission_id', sa.INTEGER(), autoincrement=False, nullable=True),
	sa.Column('comment_id', sa.INTEGER(), autoincrement=False, nullable=True),
	sa.Column('kind', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
	sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], name='award_comment_fkey'),
	sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], name='award_submission_fkey'),
	sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='award_user_fkey'),
	sa.PrimaryKeyConstraint('id', name='award_relationships_pkey'),
	sa.UniqueConstraint('user_id', 'submission_id', 'comment_id', name='award_constraint')
	)
	op.create_index('award_user_idx', 'award_relationships', ['user_id'], unique=False)
	op.create_index('award_post_idx', 'award_relationships', ['submission_id'], unique=False)
	op.create_index('award_comment_idx', 'award_relationships', ['comment_id'], unique=False)
