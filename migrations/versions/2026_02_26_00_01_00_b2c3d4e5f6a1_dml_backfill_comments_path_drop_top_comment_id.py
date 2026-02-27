"""DML: backfill comments.path and drop top_comment_id

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-02-26 00:01:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Backfill path for root comments (level=1): path = id
    op.execute("UPDATE comments SET path = id::text::ltree WHERE level = 1")

    # Backfill path for nested comments level-by-level using existing level column
    op.execute("""
        DO $$
        DECLARE max_level INT;
        BEGIN
            SELECT MAX(level) INTO max_level FROM comments WHERE parent_submission IS NOT NULL;
            FOR i IN 2..max_level LOOP
                UPDATE comments c
                SET path = p.path || c.id::text
                FROM comments p
                WHERE c.parent_comment_id = p.id AND c.level = i;
            END LOOP;
        END $$;
    """)

    # Handle DM/notification comments (parent_submission IS NULL) that are still null:
    # these are root-level messages, set path = id
    op.execute("UPDATE comments SET path = id::text::ltree WHERE path IS NULL")

    # Make path NOT NULL now that all rows are populated
    op.execute("ALTER TABLE comments ALTER COLUMN path SET NOT NULL")

    # Drop the now-redundant top_comment_id column
    op.drop_column('comments', 'top_comment_id')


def downgrade():
    op.add_column('comments', sa.Column('top_comment_id', sa.Integer(), nullable=True))
    # Restore top_comment_id from path: root segment of path is the top_comment_id
    op.execute(
        "UPDATE comments SET top_comment_id = subpath(path, 0, 1)::text::int"
    )
    op.execute("ALTER TABLE comments ALTER COLUMN path DROP NOT NULL")
