"""Remove duplicate unique constraints covered by unique indexes.

Revision ID: 003_unique_cleanup
Revises: 002_auth_sessions_and_otp
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_unique_cleanup"
down_revision: Union[str, None] = "002_auth_sessions_and_otp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_constraint("uq_source_records_source_id", "source_records", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint(
        "uq_source_records_source_id",
        "source_records",
        ["source_id"],
    )
