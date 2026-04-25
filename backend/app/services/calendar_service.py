"""Calendar generation algorithms (US1) — no external libraries.

Round-robin uses the classic circle method with a ghost player for odd N.
Single-elim assigns byes to the most-recently-inscribed participants so the
surviving bracket is a power of two.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MatchPlan:
    """Pure-Python representation of a match before it is persisted."""

    player1_id: uuid.UUID
    player2_id: uuid.UUID | None
    is_bye: bool
    round_number: int
    bracket_position: int | None = None
    tournament_code: str | None = None
    code_created_at: datetime | None = None


@dataclass
class Round:
    number: int
    matches: list[MatchPlan] = field(default_factory=list)


def _uuid_code() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sort_participants(participants) -> list:
    """Deterministic ordering: accepted_at ASC, id ASC as stable tiebreak."""
    return sorted(participants, key=lambda p: (p.accepted_at, str(p.id)))


def generate_round_robin(participants) -> list[Round]:
    """Circle-method rotation. Returns all rounds for the tournament.

    With N even: N-1 rounds of N/2 matches each.
    With N odd: add a ghost player (bye); N rounds; each real player rests
    exactly once.
    """
    if len(participants) < 2:
        raise ValueError("need at least 2 participants for round-robin")

    ordered = _sort_participants(participants)
    players: list = list(ordered)
    ghost = None  # sentinel for the ghost slot
    if len(players) % 2 == 1:
        players.append(ghost)
    n = len(players)
    total_rounds = n - 1

    fixed = players[0]
    rotating = players[1:]

    rounds: list[Round] = []
    for r in range(total_rounds):
        round_players = [fixed] + rotating
        matches: list[MatchPlan] = []
        for i in range(n // 2):
            p1 = round_players[i]
            p2 = round_players[n - 1 - i]
            if p1 is ghost or p2 is ghost:
                real = p2 if p1 is ghost else p1
                matches.append(
                    MatchPlan(
                        player1_id=real.id,
                        player2_id=None,
                        is_bye=True,
                        round_number=r + 1,
                        bracket_position=None,
                        tournament_code=None,
                        code_created_at=None,
                    )
                )
            else:
                matches.append(
                    MatchPlan(
                        player1_id=p1.id,
                        player2_id=p2.id,
                        is_bye=False,
                        round_number=r + 1,
                        bracket_position=None,
                        tournament_code=_uuid_code(),
                        code_created_at=_now(),
                    )
                )
        rounds.append(Round(number=r + 1, matches=matches))
        rotating = [rotating[-1]] + rotating[:-1]

    return rounds


def generate_single_elim_first_round(participants) -> Round:
    """Generate only the first round. Subsequent rounds are generated when the
    previous one closes (see match_service.close_round_and_generate_next).
    """
    if len(participants) < 2:
        raise ValueError("need at least 2 participants for single-elim")

    ordered = _sort_participants(participants)  # ASC by accepted_at
    n = len(ordered)
    bracket_size = 1
    while bracket_size < n:
        bracket_size *= 2
    byes_count = bracket_size - n

    # Byes go to the most recently inscribed (DESC by accepted_at).
    bye_players = list(reversed(ordered))[:byes_count]
    bye_ids = {p.id for p in bye_players}
    playing = [p for p in ordered if p.id not in bye_ids]

    matches: list[MatchPlan] = []
    position = 0
    for i in range(0, len(playing), 2):
        p1 = playing[i]
        p2 = playing[i + 1]
        matches.append(
            MatchPlan(
                player1_id=p1.id,
                player2_id=p2.id,
                is_bye=False,
                round_number=1,
                bracket_position=position,
                tournament_code=_uuid_code(),
                code_created_at=_now(),
            )
        )
        position += 1
    for bp in bye_players:
        matches.append(
            MatchPlan(
                player1_id=bp.id,
                player2_id=None,
                is_bye=True,
                round_number=1,
                bracket_position=position,
                tournament_code=None,
                code_created_at=None,
            )
        )
        position += 1

    return Round(number=1, matches=matches)


def generate_next_single_elim_round(winners, round_number: int) -> Round:
    """Pair up winners (in order) into the next round."""
    if len(winners) < 2:
        return Round(number=round_number, matches=[])
    matches: list[MatchPlan] = []
    for i in range(0, len(winners), 2):
        w1 = winners[i]
        w2 = winners[i + 1] if i + 1 < len(winners) else None
        matches.append(
            MatchPlan(
                player1_id=w1,
                player2_id=w2,
                is_bye=w2 is None,
                round_number=round_number,
                bracket_position=i // 2,
                tournament_code=_uuid_code() if w2 is not None else None,
                code_created_at=_now() if w2 is not None else None,
            )
        )
    return Round(number=round_number, matches=matches)
