"""add_chats_table

Revision ID: 7d5b742beb09
Revises: f5564050bd52
Create Date: 2021-08-07 14:47:11.760099

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, BIGINT

# revision identifiers, used by Alembic.
revision = '7d5b742beb09'
down_revision = 'f5564050bd52'
branch_labels = None
depends_on = None


SERVER_NOW = sa.func.now()
SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade():
    op.create_table(
        "chats",
        sa.Column("chat_id", UUID, nullable=False, server_default=SERVER_UUID),
        sa.Column("t_chat_id", BIGINT, nullable=False),
        sa.Column(
            "added_at",
            TIMESTAMP,
            nullable=False,
            server_default=SERVER_NOW,
        ),

        sa.PrimaryKeyConstraint("chat_id"),
    )
    op.create_index(
        op.f("ix_chats_t_chat_id"),
        "chats",
        ["t_chat_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(op.f("ix_chats_t_chat_id"), table_name="chats")
    op.drop_table("chats")
