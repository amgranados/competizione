"""add riot provider/tournament ids to tournaments (Tournament-Stub-V5)

Revision ID: b8e2d4f6a1c3
Revises: a7c3f1e8b2d4
Create Date: 2026-06-11 00:00:00.000000

Two nullable INTEGER columns on `tournaments` to persist the ids returned by
Riot's Tournament-Stub-V5 when the tournament starts (provider registration +
tournament creation). NULL means the tournament pre-dates the integration,
hasn't started, or Riot was unavailable and local fallback codes were used.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e2d4f6a1c3"
down_revision: Union[str, Sequence[str], None] = "a7c3f1e8b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("riot_provider_id", sa.Integer(), nullable=True))
    op.add_column("tournaments", sa.Column("riot_tournament_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("tournaments", "riot_tournament_id")
    op.drop_column("tournaments", "riot_provider_id")
