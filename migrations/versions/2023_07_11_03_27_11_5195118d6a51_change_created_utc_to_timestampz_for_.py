"""Change created_utc to timestampz for commentvotes

Revision ID: 5195118d6a51
Revises: 7ae4658467d7
Create Date: 2023-07-11 03:27:11.520264+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql.functions import now


# revision identifiers, used by Alembic.
revision = '5195118d6a51'
down_revision = '7ae4658467d7'
branch_labels = None
depends_on = None

table_name = 'commentvotes'
from_column = 'created_utc'
to_column = 'created_datetimez'

def upgrade():
    op.add_column(table_name, sa.Column(to_column, sa.DateTime(timezone=True), server_default=now(), nullable=True))
    op.execute(f"""
        UPDATE {table_name} 
        SET {to_column} = 
            CASE 
                WHEN {from_column} > 0 THEN 
                    (timestamp 'epoch' + {from_column} * interval '1 second') at time zone 'utc' 
                ELSE NULL 
            END
    """)

    op.alter_column(table_name, to_column, nullable=False)
    op.drop_column(table_name, from_column)


def downgrade():
    op.add_column(table_name, sa.Column(from_column, sa.INTEGER(), server_default=sa.text('0'), nullable=True))
    op.execute(f"""
        UPDATE {table_name} 
        SET {from_column} = 
            COALESCE(
                EXTRACT(EPOCH FROM {to_column})::integer,
                0
            )
        """)
    op.alter_column(table_name, from_column, nullable=False)
    op.drop_column(table_name, to_column)
