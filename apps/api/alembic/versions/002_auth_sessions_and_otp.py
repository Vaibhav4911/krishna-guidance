"""Persist revocable login sessions and one-time email challenges.

Revision ID: 002_auth_sessions_and_otp
Revises: 001_initial_schema
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_auth_sessions_and_otp"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_subject", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_google_subject", "users", ["google_subject"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_auth_sessions_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table(
        "otp_challenges",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_otp_challenges_email_created_at",
        "otp_challenges",
        ["email", "created_at"],
    )
    op.create_index("ix_otp_challenges_email", "otp_challenges", ["email"])


def downgrade() -> None:
    op.drop_index("ix_otp_challenges_email", table_name="otp_challenges")
    op.drop_index("ix_otp_challenges_email_created_at", table_name="otp_challenges")
    op.drop_table("otp_challenges")

    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")

    op.drop_constraint("uq_users_google_subject", "users", type_="unique")
    op.drop_column("users", "google_subject")
