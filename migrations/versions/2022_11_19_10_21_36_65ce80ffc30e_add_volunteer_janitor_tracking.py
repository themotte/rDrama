"""Add volunteer janitor tracking.

Revision ID: 65ce80ffc30e
Revises: d7a4a6723411
Create Date: 2022-11-19 10:21:36.385505+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '65ce80ffc30e'
down_revision = 'd7a4a6723411'
branch_labels = None
depends_on = None


def upgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	op.create_table('volunteer_janitor',
	sa.Column('id', sa.Integer(), nullable=False),
	sa.Column('user_id', sa.Integer(), nullable=False),
	sa.Column('comment_id', sa.Integer(), nullable=False),
	sa.Column('edited_utc', sa.DateTime(), nullable=False),
	sa.Column('result', sa.Enum('Pending', 'TopQuality', 'Good', 'Neutral', 'Bad', 'Warning', 'Ban', name='volunteerjanitorresult'), nullable=False),
	sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ),
	sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
	sa.PrimaryKeyConstraint('id')
	)
	op.create_index('volunteer_comment_index', 'volunteer_janitor', ['user_id', 'comment_id'], unique=False)
	# ### end Alembic commands ###


def downgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	op.drop_index('volunteer_comment_index', table_name='volunteer_janitor')
	op.drop_table('volunteer_janitor')
	# ### end Alembic commands ###
