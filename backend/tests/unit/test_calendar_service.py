"""Unit tests for calendar_service (US1).

Covers T010-T016: round-robin rotation (circle method), single-elim byes,
determinism, completeness, fairness-bye, tournament code uniqueness.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.services import calendar_service


@dataclass(frozen=True)
class FakeParticipant:
    """Stand-in for the Participant model used by the pure algorithm."""

    id: uuid.UUID
    accepted_at: datetime


def make_participants(n: int, base_time: datetime | None = None) -> list[FakeParticipant]:
    base_time = base_time or datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        FakeParticipant(id=uuid.uuid4(), accepted_at=base_time + timedelta(minutes=i))
        for i in range(n)
    ]


# ------------------------------- round-robin -------------------------------


def test_round_robin_even_pairs_everyone_once():
    participants = make_participants(4)
    rounds = calendar_service.generate_round_robin(participants)

    assert len(rounds) == 3  # N-1 rounds for N=4
    all_pairs: set[frozenset[uuid.UUID]] = set()
    for r in rounds:
        for m in r.matches:
            assert not m.is_bye
            all_pairs.add(frozenset([m.player1_id, m.player2_id]))

    expected_pairs = {
        frozenset([a.id, b.id]) for i, a in enumerate(participants) for b in participants[i + 1 :]
    }
    assert all_pairs == expected_pairs  # completeness
    assert sum(len(r.matches) for r in rounds) == 6  # 4*3/2


def test_round_robin_odd_every_player_rests_exactly_once():
    participants = make_participants(5)
    rounds = calendar_service.generate_round_robin(participants)

    assert len(rounds) == 5  # for N odd, N rounds
    byes_per_player: dict[uuid.UUID, int] = {p.id: 0 for p in participants}
    for r in rounds:
        bye_matches = [m for m in r.matches if m.is_bye]
        assert len(bye_matches) == 1
        byes_per_player[bye_matches[0].player1_id] += 1

    assert all(count == 1 for count in byes_per_player.values())  # fairness-bye


def test_round_robin_is_deterministic():
    participants = make_participants(4)
    r1 = calendar_service.generate_round_robin(participants)
    r2 = calendar_service.generate_round_robin(participants)

    def flatten(rs):
        return [
            (r.number, m.player1_id, m.player2_id, m.is_bye)
            for r in rs
            for m in r.matches
        ]

    assert flatten(r1) == flatten(r2)


def test_round_robin_bye_has_no_tournament_code():
    participants = make_participants(5)
    rounds = calendar_service.generate_round_robin(participants)
    for r in rounds:
        for m in r.matches:
            if m.is_bye:
                assert m.tournament_code is None
                assert m.code_created_at is None


def test_round_robin_non_bye_matches_get_unique_uuid_tournament_codes():
    participants = make_participants(4)
    rounds = calendar_service.generate_round_robin(participants)
    codes = [m.tournament_code for r in rounds for m in r.matches if not m.is_bye]

    assert all(c is not None for c in codes)
    assert len(codes) == len(set(codes))
    for c in codes:
        uuid.UUID(c)  # must be a valid UUID string


# ---------------------------- single elimination ---------------------------


def test_single_elim_with_6_participants_assigns_2_byes_to_most_recent():
    participants = make_participants(6)  # ordered ASC by accepted_at
    round1 = calendar_service.generate_single_elim_first_round(participants)

    assert round1.number == 1
    byes = [m for m in round1.matches if m.is_bye]
    playing = [m for m in round1.matches if not m.is_bye]
    assert len(byes) == 2
    assert len(playing) == 2

    bye_player_ids = {m.player1_id for m in byes}
    recent_two_ids = {participants[-1].id, participants[-2].id}
    assert bye_player_ids == recent_two_ids

    # the 4 players without bye are the 4 oldest, paired 1v2 and 3v4 in accepted_at ASC order
    expected_playing_pairs = [
        (participants[0].id, participants[1].id),
        (participants[2].id, participants[3].id),
    ]
    actual = sorted([(m.player1_id, m.player2_id) for m in playing])
    expected = sorted(expected_playing_pairs)
    assert actual == expected


def test_single_elim_first_round_is_deterministic():
    participants = make_participants(5)
    r1 = calendar_service.generate_single_elim_first_round(participants)
    r2 = calendar_service.generate_single_elim_first_round(participants)

    def key(r):
        return sorted((m.player1_id, m.player2_id, m.is_bye) for m in r.matches)

    assert key(r1) == key(r2)


def test_single_elim_power_of_two_has_no_byes():
    participants = make_participants(4)
    round1 = calendar_service.generate_single_elim_first_round(participants)
    assert all(not m.is_bye for m in round1.matches)
    assert len(round1.matches) == 2


def test_single_elim_bye_has_no_code():
    participants = make_participants(3)  # 1 bye expected
    round1 = calendar_service.generate_single_elim_first_round(participants)
    byes = [m for m in round1.matches if m.is_bye]
    assert len(byes) == 1
    assert byes[0].tournament_code is None


def test_single_elim_non_bye_matches_get_unique_codes():
    participants = make_participants(6)
    round1 = calendar_service.generate_single_elim_first_round(participants)
    codes = [m.tournament_code for m in round1.matches if not m.is_bye]
    assert all(c is not None for c in codes)
    assert len(codes) == len(set(codes))
    for c in codes:
        uuid.UUID(c)


def test_single_elim_rejects_less_than_two_participants():
    participants = make_participants(1)
    with pytest.raises(ValueError):
        calendar_service.generate_single_elim_first_round(participants)


def test_round_robin_rejects_less_than_two_participants():
    participants = make_participants(1)
    with pytest.raises(ValueError):
        calendar_service.generate_round_robin(participants)


# ----------------------- property tests (Polish) ----------------------------


@pytest.mark.parametrize("n", list(range(2, 17)))
def test_round_robin_completeness_for_N_up_to_16(n):
    participants = make_participants(n)
    rounds = calendar_service.generate_round_robin(participants)

    all_pairs: set[frozenset[uuid.UUID]] = set()
    bye_count: dict[uuid.UUID, int] = {p.id: 0 for p in participants}
    for r in rounds:
        for m in r.matches:
            if m.is_bye:
                bye_count[m.player1_id] += 1
            else:
                all_pairs.add(frozenset([m.player1_id, m.player2_id]))

    expected_pairs = {
        frozenset([a.id, b.id]) for i, a in enumerate(participants) for b in participants[i + 1 :]
    }
    assert all_pairs == expected_pairs

    if n % 2 == 1:
        # fairness-bye: each real player rests exactly once
        assert all(count == 1 for count in bye_count.values())
    else:
        assert all(count == 0 for count in bye_count.values())


@pytest.mark.parametrize("n", list(range(2, 17)))
def test_single_elim_first_round_balances_bracket(n):
    participants = make_participants(n)
    round1 = calendar_service.generate_single_elim_first_round(participants)
    bracket_size = 1
    while bracket_size < n:
        bracket_size *= 2
    expected_byes = bracket_size - n
    actual_byes = sum(1 for m in round1.matches if m.is_bye)
    assert actual_byes == expected_byes
    # Number of players surviving round 1 = n - (matches that play)/2 wins + byes
    plays = [m for m in round1.matches if not m.is_bye]
    survivors = len(plays) + actual_byes  # winners + byes
    # Survivors must be a power of 2 (or 1 if final already)
    assert survivors == bracket_size // 2 or survivors == 1
