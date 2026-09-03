"""Round-robin standings computation (US4).

Implements FR-047 and FR-048. Tie-breaking order:
1. wins DESC
2. head-to-head among tied (only resolves pairs)
3. inscription date ASC (handles circular tie)
4. participant.id ASC (stable, deterministic last resort)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.participant import Participant
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.tournament import StandingEntry


@dataclass
class _Stats:
    participant: Participant
    user_nickname: str
    wins: int = 0
    losses: int = 0
    byes: int = 0


def _direct_winner(matches: list[Match], a: uuid.UUID, b: uuid.UUID) -> uuid.UUID | None:
    """Return the winner of the direct match between a and b, or None if no
    decided match exists."""
    for m in matches:
        if m.is_bye:
            continue
        if m.state == "pending":
            continue
        if {m.player1_id, m.player2_id} == {a, b}:
            return m.winner_participant_id
    return None


async def compute(session: AsyncSession, tournament: Tournament) -> list[StandingEntry]:
    """Build the round-robin standings table for the tournament."""
    # Fetch participants + user nicknames.
    stmt = (
        select(Participant, User.nickname)
        .join(User, User.id == Participant.user_id)
        .where(Participant.tournament_id == tournament.id, Participant.removed.is_(False))
    )
    rows = (await session.execute(stmt)).all()
    if not rows:
        return []

    stats: dict[uuid.UUID, _Stats] = {
        p.id: _Stats(participant=p, user_nickname=nick) for p, nick in rows
    }

    matches_result = await session.execute(
        select(Match).where(Match.tournament_id == tournament.id)
    )
    matches = list(matches_result.scalars().all())

    for m in matches:
        if m.is_bye:
            if m.player1_id in stats:
                stats[m.player1_id].byes += 1
            continue
        if m.state == "pending" or m.winner_participant_id is None:
            continue
        winner = stats.get(m.winner_participant_id)
        if winner is None:
            continue
        winner.wins += 1
        loser_id = m.player2_id if m.winner_participant_id == m.player1_id else m.player1_id
        loser = stats.get(loser_id)
        if loser is not None:
            loser.losses += 1

    # Sort with the 4-step rule. We use a key that handles steps 1, 3, 4 and a
    # post-sort pass for the head-to-head step (only re-orders adjacent ties).
    keyed = sorted(
        stats.values(),
        key=lambda s: (-s.wins, s.participant.accepted_at, str(s.participant.id)),
    )

    # Apply head-to-head between equal-points pairs (single direct match).
    # Walk groups of equal points and resolve adjacent reversals when the
    # second beat the first. Circular ties remain in inscription/id order.
    n = len(keyed)
    i = 0
    while i < n:
        j = i + 1
        while j < n and keyed[j].wins == keyed[i].wins:
            j += 1
        # group = keyed[i:j] all tied on wins; resolve via simple bubble-style swap
        group = keyed[i:j]
        if len(group) == 2:
            winner = _direct_winner(matches, group[0].participant.id, group[1].participant.id)
            if winner == group[1].participant.id:
                keyed[i], keyed[i + 1] = keyed[i + 1], keyed[i]
        i = j

    # Build the result with rank and points.
    entries: list[StandingEntry] = []
    for rank, s in enumerate(keyed, start=1):
        entries.append(
            StandingEntry(
                participant_id=s.participant.id,
                user_id=s.participant.user_id,
                nickname=s.user_nickname,
                wins=s.wins,
                losses=s.losses,
                byes=s.byes,
                points=s.wins,
                rank=rank,
            )
        )
    return entries
