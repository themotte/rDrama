"""Change created_utc to timestampz for commentvotes

Revision ID: 5195118d6a51
Revises: 7ae4658467d7
Create Date: 2023-07-11 03:27:11.520264+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5195118d6a51'
down_revision = '7ae4658467d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('commentvotes', sa.Column('created_timestampz', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.execute("""
        UPDATE commentvotes 
        SET created_timestampz = 
            CASE 
                WHEN created_utc > 0 THEN 
                    (timestamp 'epoch' + created_utc * interval '1 second') at time zone 'utc' 
                ELSE NULL 
            END
    """)

    op.drop_column('commentvotes', 'created_utc')


def downgrade():
    op.add_column('commentvotes', sa.Column('created_utc', sa.INTEGER(), server_default=sa.text('0'), nullable=True))
    op.execute("""
        UPDATE commentvotes 
        SET created_utc = 
            COALESCE(
                EXTRACT(EPOCH FROM created_timestampz)::integer,
                0
            )
        """)
    op.alter_column('commentvotes', 'created_utc', nullable=False)
    op.drop_column('commentvotes', 'created_timestampz')
