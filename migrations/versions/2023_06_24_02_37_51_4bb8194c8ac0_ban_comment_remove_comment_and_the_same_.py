"""ban_comment->remove_comment, and the same for posts

Revision ID: 4bb8194c8ac0
Revises: 8337558f4f36
Create Date: 2023-06-24 02:37:51.984484+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4bb8194c8ac0'
down_revision = '8337558f4f36'
branch_labels = None
depends_on = None


def upgrade():
    # update for comments
    op.execute(sa.text("""UPDATE modactions SET kind = 'remove_comment' WHERE kind = 'ban_comment'"""))
    op.execute(sa.text("""UPDATE modactions SET kind = 'unremove_comment' WHERE kind = 'unban_comment'"""))
    # update for posts
    op.execute(sa.text("""UPDATE modactions SET kind = 'remove_post' WHERE kind = 'ban_post'"""))
    op.execute(sa.text("""UPDATE modactions SET kind = 'unremove_post' WHERE kind = 'unban_post'"""))

def downgrade():
    # rollback for comments
    op.execute(sa.text("""UPDATE modactions SET kind = 'ban_comment' WHERE kind = 'remove_comment'"""))
    op.execute(sa.text("""UPDATE modactions SET kind = 'unban_comment' WHERE kind = 'unremove_comment'"""))
    # rollback for posts
    op.execute(sa.text("""UPDATE modactions SET kind = 'ban_post' WHERE kind = 'remove_post'"""))
    op.execute(sa.text("""UPDATE modactions SET kind = 'unban_post' WHERE kind = 'unremove_post'"""))