"""add_actions_table

Revision ID: 86d9276c9767
Revises: 9993a9fb4595
Create Date: 2021-08-07 14:47:17.072232

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, VARCHAR, TIMESTAMP, FLOAT

# revision identifiers, used by Alembic.
revision = '86d9276c9767'
down_revision = '9993a9fb4595'
branch_labels = None
depends_on = None


SERVER_NOW = sa.func.now()
SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade():
    op.create_table(
        "actions",
        sa.Column(
            "action_id",
            UUID,
            nullable=False,
            server_default=SERVER_UUID,
        ),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column(
            "added_at",
            TIMESTAMP,
            nullable=False,
            server_default=SERVER_NOW,
        ),
        sa.Column("amount", FLOAT, nullable=False),
        sa.Column("comment", VARCHAR(128), nullable=False),

        sa.PrimaryKeyConstraint("action_id"),
        sa.ForeignKeyConstraint(
            columns=("user_id",),
            refcolumns=("users.user_id",),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_actions_user_id"),
        "actions",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_actions_user_id"), table_name="actions")
    op.drop_table("actions")
