"""Initial schema for Krishna Guidance

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-10 21:54:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_conversations_user_id_users"),
    )
    op.create_index(op.f("ix_conversations_id"), "conversations", ["id"], unique=False)
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_chat_messages_conversation_id_conversations"),
    )
    op.create_index(op.f("ix_chat_messages_conversation_id"), "chat_messages", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_chat_messages_id"), "chat_messages", ["id"], unique=False)

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mood", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_journal_entries_user_id_users"),
    )
    op.create_index(op.f("ix_journal_entries_id"), "journal_entries", ["id"], unique=False)
    op.create_index(op.f("ix_journal_entries_user_id"), "journal_entries", ["user_id"], unique=False)

    op.create_table(
        "favorite_verses",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chapter", sa.Integer(), nullable=False),
        sa.Column("verse", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False, server_default="Bhagavad Gita"),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_favorite_verses_user_id_users"),
    )
    op.create_index(op.f("ix_favorite_verses_id"), "favorite_verses", ["id"], unique=False)
    op.create_index(op.f("ix_favorite_verses_user_id"), "favorite_verses", ["user_id"], unique=False)

    op.create_table(
        "source_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("rights_status", sa.String(length=32), nullable=False, server_default="approved"),
        sa.Column("corpus_version", sa.String(length=128), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("source_id", name="uq_source_records_source_id"),
    )
    op.create_index(op.f("ix_source_records_id"), "source_records", ["id"], unique=False)
    op.create_index(op.f("ix_source_records_source_id"), "source_records", ["source_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_source_records_source_id"), table_name="source_records")
    op.drop_index(op.f("ix_source_records_id"), table_name="source_records")
    op.drop_table("source_records")

    op.drop_index(op.f("ix_favorite_verses_user_id"), table_name="favorite_verses")
    op.drop_index(op.f("ix_favorite_verses_id"), table_name="favorite_verses")
    op.drop_table("favorite_verses")

    op.drop_index(op.f("ix_journal_entries_user_id"), table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_id"), table_name="journal_entries")
    op.drop_table("journal_entries")

    op.drop_index(op.f("ix_chat_messages_conversation_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_id"), table_name="conversations")
    op.drop_table("conversations")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
