"""Replace Google and email OTP auth with email/password accounts.

Revision ID: 004_email_password_auth
Revises: 003_unique_cleanup
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_email_password_auth"
down_revision: Union[str, None] = "003_unique_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.drop_table("otp_challenges")
    op.drop_constraint("uq_users_google_subject", "users", type_="unique")
    op.drop_column("users", "google_subject")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("google_subject", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_users_google_subject",
        "users",
        ["google_subject"],
    )
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
    op.drop_column("users", "password_hash")
