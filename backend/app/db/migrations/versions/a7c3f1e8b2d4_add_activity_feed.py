"""add activity_feed table (005-user-dashboard)

Revision ID: a7c3f1e8b2d4
Revises: e2a4b5c7d9f1
Create Date: 2026-06-09 00:00:00.000000

Adds the single new table for the dashboard feature. No existing table is
altered (data-model.md). Events are written at the moment of the action and the
dashboard reads the 6 most recent visible to the user.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7c3f1e8b2d4"
down_revision: Union[str, Sequence[str], None] = "e2a4b5c7d9f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create `activity_feed`:

    - `event_type` is a non-native Enum (`native_enum=False, create_constraint=True`)
      so it is realized as VARCHAR + CHECK on both SQLite and PostgreSQL — same
      approach as `friendship_status` (004). No PostgreSQL enum type is created.
    - `actor_id` FK → users ON DELETE CASCADE; `tournament_id` FK → tournaments
      ON DELETE SET NULL (nullable) so the actor's event survives tournament
      deletion (FR-022).
    - `idx_activity_actor_created` on (actor_id, created_at) serves the feed query.
    """
    op.create_table(
        "activity_feed",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "MATCH_WIN",
                "TOURNAMENT_JOIN",
                "TOURNAMENT_INVITE",
                "TOURNAMENT_CREATE",
                name="activity_event_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("tournament_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_feed_actor_id", "activity_feed", ["actor_id"], unique=False)
    op.create_index(
        "ix_activity_feed_tournament_id", "activity_feed", ["tournament_id"], unique=False
    )
    op.create_index(
        "idx_activity_actor_created",
        "activity_feed",
        ["actor_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the table, its indexes and the enum CHECK constraint (all are part of
    the table definition, so a single drop_table removes them)."""
    op.drop_index("idx_activity_actor_created", table_name="activity_feed")
    op.drop_index("ix_activity_feed_tournament_id", table_name="activity_feed")
    op.drop_index("ix_activity_feed_actor_id", table_name="activity_feed")
    op.drop_table("activity_feed")
