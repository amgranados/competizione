"""riot_accounts: store the Riot ID (game_name + tag_line)

Revision ID: c4d7c2f1abcd
Revises: b3f7a51e9d24
Create Date: 2026-04-27 00:00:00.000000

The simplified profile flow stores the Riot ID alongside the PUUID so the UI
can display it back to the user. The `region` column added in b3f7a51e9d24
stays — it now holds the platform code (EUW1, NA1, KR, ...) used to query
champion-mastery/v4 on platform hosts.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4d7c2f1abcd"
down_revision: Union[str, Sequence[str], None] = "b3f7a51e9d24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("riot_accounts") as batch_op:
        batch_op.add_column(
            sa.Column("game_name", sa.String(length=64), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("tag_line", sa.String(length=16), nullable=False, server_default="")
        )


def downgrade() -> None:
    with op.batch_alter_table("riot_accounts") as batch_op:
        batch_op.drop_column("tag_line")
        batch_op.drop_column("game_name")
