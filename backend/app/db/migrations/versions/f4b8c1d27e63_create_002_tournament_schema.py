"""create 002 tournament-management tables (tournaments, participants,
invitations, matches, notifications)

Revision ID: f4b8c1d27e63
Revises: d1f3a2b4c8e0
Create Date: 2026-04-29 03:00:00.000000

The 002 feature originally created these tables via `Base.metadata.create_all`
during dev / tests, never as a real Alembic migration. The 004 migration
`e2a4b5c7d9f1` (which adds `friendship_id` to `notifications`) therefore
broke on a fresh database with `relation "notifications" does not exist`.

This migration backfills the missing schema so the chain is self-contained:
`alembic upgrade head` works against an empty database without falling back
to `Base.metadata.create_all`.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f4b8c1d27e63"
down_revision: Union[str, Sequence[str], None] = "d1f3a2b4c8e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tournaments_organizer_id"),
        "tournaments",
        ["organizer_id"],
        unique=False,
    )

    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tournament_id", "user_id", name="uq_participant_tournament_user"
        ),
    )
    op.create_index(
        op.f("ix_participants_tournament_id"),
        "participants",
        ["tournament_id"],
        unique=False,
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("invited_user_id", sa.Uuid(), nullable=False),
        sa.Column("inviter_user_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invitations_tournament_id"),
        "invitations",
        ["tournament_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invitations_invited_user_id"),
        "invitations",
        ["invited_user_id"],
        unique=False,
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("bracket_position", sa.Integer(), nullable=True),
        sa.Column("player1_id", sa.Uuid(), nullable=False),
        sa.Column("player2_id", sa.Uuid(), nullable=True),
        sa.Column("is_bye", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tournament_code", sa.String(length=64), nullable=True),
        sa.Column("code_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("winner_participant_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player1_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player2_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["winner_participant_id"], ["participants.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_matches_tournament_id"),
        "matches",
        ["tournament_id"],
        unique=False,
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=True),
        sa.Column("match_id", sa.Uuid(), nullable=True),
        sa.Column("invitation_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invitation_id"], ["invitations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notifications_user_id"),
        "notifications",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_matches_tournament_id"), table_name="matches")
    op.drop_table("matches")
    op.drop_index(op.f("ix_invitations_invited_user_id"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_tournament_id"), table_name="invitations")
    op.drop_table("invitations")
    op.drop_index(op.f("ix_participants_tournament_id"), table_name="participants")
    op.drop_table("participants")
    op.drop_index(op.f("ix_tournaments_organizer_id"), table_name="tournaments")
    op.drop_table("tournaments")
