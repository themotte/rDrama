"""DDL: add ltree path column to comments

Revision ID: a1b2c3d4e5f6
Revises: 3023741ec9dd
Create Date: 2026-02-26 00:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3023741ec9dd'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")
    op.add_column('comments', sa.Column('path', sa.Text(), nullable=True))
    op.execute("ALTER TABLE comments ALTER COLUMN path TYPE ltree USING path::ltree")
    op.create_index(
        'comments_path_gist_index',
        'comments',
        ['path'],
        postgresql_using='gist'
    )
    op.execute(
        "CREATE INDEX comments_path_root_index ON comments "
        "USING btree (subpath(path, 0, 1))"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS comments_path_root_index")
    op.drop_index('comments_path_gist_index', table_name='comments')
    op.drop_column('comments', 'path')
