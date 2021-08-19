"""add_users_table

Revision ID: 9993a9fb4595
Revises: 7d5b742beb09
Create Date: 2021-08-07 14:47:13.932851

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, VARCHAR

# revision identifiers, used by Alembic.
revision = '9993a9fb4595'
down_revision = '7d5b742beb09'
branch_labels = None
depends_on = None


SERVER_NOW = sa.func.now()
SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade():
    op.create_table(
        "users",
        sa.Column("user_id", UUID, nullable=False, server_default=SERVER_UUID),
        sa.Column("chat_id", UUID, nullable=False),
        sa.Column("name", VARCHAR(128), nullable=False),
        sa.Column(
            "added_at",
            TIMESTAMP,
            nullable=False,
            server_default=SERVER_NOW,
        ),

        sa.PrimaryKeyConstraint("user_id"),
        sa.ForeignKeyConstraint(
            columns=("chat_id",),
            refcolumns=("chats.chat_id",),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_users_chat_name"),
        "users",
        ["chat_id", "name"],
        unique=True,
    )


def downgrade():
    op.drop_index(op.f("ix_users_chat_name"), table_name="users")
    op.drop_table("users")
