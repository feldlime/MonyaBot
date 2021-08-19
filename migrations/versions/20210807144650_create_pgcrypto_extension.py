"""create_pgcrypto_extension

Revision ID: f5564050bd52
Revises:
Create Date: 2021-08-07 14:46:50.754060

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5564050bd52'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")


def downgrade():
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
