"""add avatar_url, deleted_at and riot_accounts (003-edit-profile)

Revision ID: b3f7a51e9d24
Revises: 7dcf00c02c11
Create Date: 2026-04-25 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b3f7a51e9d24"
down_revision: Union[str, Sequence[str], None] = "7dcf00c02c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for 003-edit-profile.

    1. Add `avatar_url` (nullable) to `users`.
    2. Add `deleted_at` (nullable) to `users` for the anonymization marker (HD-4).
    3. Allow `users.email` to be nullable so anonymization can NULL it.
    4. Create the `riot_accounts` table linking a user to a single LoL account
       via PUUID + region. Credentials (game_name/tag_line) are NEVER stored.
    """
    # batch_alter_table supports SQLite (table-rename trick) and is a no-op
    # ALTER on PostgreSQL — works on both dev (sqlite) and prod (postgres).
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("avatar_url", sa.String(length=2048), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.alter_column(
            "email", existing_type=sa.String(length=320), nullable=True
        )

    op.create_table(
        "riot_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("puuid", sa.String(length=78), nullable=False),
        sa.Column("region", sa.String(length=8), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_riot_account_user"),
    )
    op.create_index(op.f("ix_riot_accounts_user_id"), "riot_accounts", ["user_id"], unique=False)
    op.create_index(op.f("ix_riot_accounts_puuid"), "riot_accounts", ["puuid"], unique=True)


def downgrade() -> None:
    """Revert 003 schema changes."""
    op.drop_index(op.f("ix_riot_accounts_puuid"), table_name="riot_accounts")
    op.drop_index(op.f("ix_riot_accounts_user_id"), table_name="riot_accounts")
    op.drop_table("riot_accounts")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "email", existing_type=sa.String(length=320), nullable=False
        )
        batch_op.drop_column("password_changed_at")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("avatar_url")
