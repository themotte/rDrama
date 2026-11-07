"""keep revoked API apps that made posts or comments

Revision ID: c9e3a7d1f5b2
Revises: b4d8f2a6c1e9
Create Date: 2026-11-07 13:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9e3a7d1f5b2'
down_revision = 'b4d8f2a6c1e9'
branch_labels = None
depends_on = None


def upgrade():
	op.add_column('oauth_apps', sa.Column('revoked_utc', sa.DateTime(timezone=True), nullable=True))
	op.create_check_constraint('oauth_apps_revoked_have_no_client_id', 'oauth_apps', 'revoked_utc IS NULL OR client_id IS NULL')


def downgrade():
	op.drop_constraint('oauth_apps_revoked_have_no_client_id', 'oauth_apps', type_='check')
	op.drop_column('oauth_apps', 'revoked_utc')
