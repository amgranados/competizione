"""add friendship_id to notifications (004-add-friends, fix #3)

Revision ID: e2a4b5c7d9f1
Revises: d1f3a2b4c8e0
Create Date: 2026-04-29 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e2a4b5c7d9f1"
down_revision: Union[str, Sequence[str], None] = "d1f3a2b4c8e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add friendship_id FK to notifications so we can attach friendship-related
    notifications to a Friendship row."""
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("friendship_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_notifications_friendship",
            "friendships",
            ["friendship_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("fk_notifications_friendship", type_="foreignkey")
        batch_op.drop_column("friendship_id")
