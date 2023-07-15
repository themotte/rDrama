"""Change created_utc to datetimez for commentflags

Revision ID: 7ae4658467d7
Revises: ea282d7c711c
Create Date: 2023-07-09 21:52:50.386177+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7ae4658467d7'
down_revision = 'ea282d7c711c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('commentflags', sa.Column('created_datetimez', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('NOW()')))
    op.execute("""
        UPDATE commentflags 
        SET created_datetimez = 
            CASE 
                WHEN created_utc > 0 THEN 
                    (timestamp 'epoch' + created_utc * interval '1 second') at time zone 'utc' 
                ELSE NULL 
            END
    """)
    op.alter_column('commentflags', 'created_datetimez', nullable=False)
    op.drop_column('commentflags', 'created_utc')


def downgrade():
    """
    Downgrade will truncate the milliseconds.
    """
    op.add_column('commentflags', sa.Column('created_utc', sa.INTEGER(), server_default=sa.text('0'), nullable=True))
    op.execute("""
        UPDATE commentflags 
        SET created_utc = 
            COALESCE(
                EXTRACT(EPOCH FROM created_datetimez)::integer,
                0
            )
        """)
    op.alter_column('commentflags', 'created_utc', nullable=False)
    op.drop_column('commentflags', 'created_datetimez')
