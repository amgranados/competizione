"""add friendships table (004-add-friends)

Revision ID: d1f3a2b4c8e0
Revises: c4d7c2f1abcd
Create Date: 2026-04-28 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d1f3a2b4c8e0"
down_revision: Union[str, Sequence[str], None] = "c4d7c2f1abcd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for 004-add-friends.

    1. Create the `friendship_status` PostgreSQL enum (`pending`, `accepted`).
       On SQLite (dev/tests) `Enum` decays to `VARCHAR + CHECK` automatically.
    2. Create the `friendships` table with:
       - UNIQUE (requester_id, addressee_id)
       - CHECK (requester_id <> addressee_id)
       - Two indexes for the relationship-status query (HD-1 / data-model.md).
    """
    op.create_table(
        "friendships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requester_id", sa.Uuid(), nullable=False),
        sa.Column("addressee_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "accepted", name="friendship_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["addressee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
        sa.CheckConstraint("requester_id <> addressee_id", name="ck_friendship_no_self"),
    )
    op.create_index(
        "idx_friendships_requester",
        "friendships",
        ["requester_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_friendships_addressee",
        "friendships",
        ["addressee_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Revert 004 schema changes."""
    op.drop_index("idx_friendships_addressee", table_name="friendships")
    op.drop_index("idx_friendships_requester", table_name="friendships")
    op.drop_table("friendships")
    # Drop the enum type explicitly (PostgreSQL keeps it after drop_table).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="friendship_status").drop(bind, checkfirst=True)
