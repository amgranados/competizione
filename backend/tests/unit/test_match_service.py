"""Unit tests for match_service (US3 + transitions shared with US4/US6).

Covers T063-T071: manual result registration, immutability, winner advancement,
bye auto-resolution, tournament finalization, notifications.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.activity_feed import ActivityFeed
from app.models.match import Match
from app.models.notification import Notification
from app.models.participant import Participant
from app.models.tournament import Tournament
from app.models.user import User
from app.services import match_service


def _user_factory(db_session):
    async def _make(email: str, nickname: str) -> User:
        user = User(email=email, nickname=nickname, password_hash="x")
        db_session.add(user)
        await db_session.flush()
        return user

    return _make


@pytest_asyncio.fixture
async def world(db_session):
    """Build a minimal single-elim world with 4 participants and round 1 ready."""
    make = _user_factory(db_session)
    u1, u2, u3, u4 = [await make(f"u{i}@x.com", f"U{i}") for i in ["a", "b", "c", "d"]]
    organizer = await make("org@x.com", "Org")

    tournament = Tournament(
        name="T", format="single_elim", state="active", organizer_id=organizer.id
    )
    db_session.add(tournament)
    await db_session.flush()

    p1 = Participant(tournament_id=tournament.id, user_id=u1.id)
    p2 = Participant(tournament_id=tournament.id, user_id=u2.id)
    p3 = Participant(tournament_id=tournament.id, user_id=u3.id)
    p4 = Participant(tournament_id=tournament.id, user_id=u4.id)
    for p in (p1, p2, p3, p4):
        db_session.add(p)
    await db_session.flush()

    m1 = Match(
        tournament_id=tournament.id,
        round_number=1,
        bracket_position=0,
        player1_id=p1.id,
        player2_id=p2.id,
        is_bye=False,
        tournament_code="tc-1",
        state="pending",
    )
    m2 = Match(
        tournament_id=tournament.id,
        round_number=1,
        bracket_position=1,
        player1_id=p3.id,
        player2_id=p4.id,
        is_bye=False,
        tournament_code="tc-2",
        state="pending",
    )
    for m in (m1, m2):
        db_session.add(m)
    await db_session.flush()
    return {
        "tournament": tournament,
        "organizer": organizer,
        "p1": p1, "p2": p2, "p3": p3, "p4": p4,
        "m1": m1, "m2": m2,
    }


@pytest.mark.asyncio
async def test_register_manual_result_marks_match_as_manual(db_session, world):
    m1 = world["m1"]
    await match_service.register_manual_result(
        db_session,
        match_id=m1.id,
        winner_participant_id=world["p1"].id,
        acting_user_id=world["organizer"].id,
    )
    await db_session.refresh(m1)
    assert m1.state == "manual"
    assert m1.winner_participant_id == world["p1"].id
    assert m1.resolved_at is not None


@pytest.mark.asyncio
async def test_manual_result_is_immutable(db_session, world):
    m1 = world["m1"]
    await match_service.register_manual_result(
        db_session,
        match_id=m1.id,
        winner_participant_id=world["p1"].id,
        acting_user_id=world["organizer"].id,
    )
    with pytest.raises(match_service.InvalidState):
        await match_service.register_manual_result(
            db_session,
            match_id=m1.id,
            winner_participant_id=world["p2"].id,
            acting_user_id=world["organizer"].id,
        )


@pytest.mark.asyncio
async def test_manual_cannot_use_non_player_as_winner(db_session, world):
    with pytest.raises(match_service.InvalidState):
        await match_service.register_manual_result(
            db_session,
            match_id=world["m1"].id,
            winner_participant_id=world["p3"].id,
            acting_user_id=world["organizer"].id,
        )


@pytest.mark.asyncio
async def test_manual_requires_organizer(db_session, world):
    with pytest.raises(match_service.Forbidden):
        await match_service.register_manual_result(
            db_session,
            match_id=world["m1"].id,
            winner_participant_id=world["p1"].id,
            acting_user_id=world["p2"].user_id,  # jugador, no organizador
        )


@pytest.mark.asyncio
async def test_manual_in_single_elim_advances_winner_to_next_round(db_session, world):
    tournament = world["tournament"]
    # Resolve m1 first (round 1). No new round yet because m2 is still pending.
    await match_service.register_manual_result(
        db_session,
        match_id=world["m1"].id,
        winner_participant_id=world["p1"].id,
        acting_user_id=world["organizer"].id,
    )
    # Still only round 1 matches.
    result = await db_session.execute(
        select(Match).where(Match.tournament_id == tournament.id, Match.round_number == 2)
    )
    assert result.scalars().first() is None

    # Resolve m2 -> round 2 is generated with winners.
    await match_service.register_manual_result(
        db_session,
        match_id=world["m2"].id,
        winner_participant_id=world["p3"].id,
        acting_user_id=world["organizer"].id,
    )
    result = await db_session.execute(
        select(Match).where(Match.tournament_id == tournament.id, Match.round_number == 2)
    )
    r2_matches = result.scalars().all()
    assert len(r2_matches) == 1
    final = r2_matches[0]
    assert {final.player1_id, final.player2_id} == {world["p1"].id, world["p3"].id}
    assert final.tournament_code is not None
    assert final.state == "pending"


@pytest.mark.asyncio
async def test_grand_final_transitions_tournament_to_finished(db_session, world):
    tournament = world["tournament"]
    # Complete round 1, then resolve the final.
    await match_service.register_manual_result(
        db_session, match_id=world["m1"].id,
        winner_participant_id=world["p1"].id,
        acting_user_id=world["organizer"].id,
    )
    await match_service.register_manual_result(
        db_session, match_id=world["m2"].id,
        winner_participant_id=world["p3"].id,
        acting_user_id=world["organizer"].id,
    )
    final = (
        await db_session.execute(
            select(Match).where(
                Match.tournament_id == tournament.id, Match.round_number == 2
            )
        )
    ).scalars().first()
    await match_service.register_manual_result(
        db_session,
        match_id=final.id,
        winner_participant_id=world["p1"].id,
        acting_user_id=world["organizer"].id,
    )
    await db_session.refresh(tournament)
    assert tournament.state == "finished"
    assert tournament.finished_at is not None


@pytest.mark.asyncio
async def test_manual_result_creates_match_resolved_notifications(db_session, world):
    await match_service.register_manual_result(
        db_session,
        match_id=world["m1"].id,
        winner_participant_id=world["p1"].id,
        acting_user_id=world["organizer"].id,
    )
    # player1 and player2 should both have a match_resolved notification.
    for participant in (world["p1"], world["p2"]):
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == participant.user_id,
                Notification.type == "match_resolved",
            )
        )
        assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_manual_cannot_register_on_bye(db_session, world):
    # Add a bye match
    tournament = world["tournament"]
    bye = Match(
        tournament_id=tournament.id,
        round_number=1,
        bracket_position=2,
        player1_id=world["p1"].id,
        player2_id=None,
        is_bye=True,
        tournament_code=None,
        state="pending",
    )
    db_session.add(bye)
    await db_session.flush()
    with pytest.raises(match_service.InvalidState):
        await match_service.register_manual_result(
            db_session,
            match_id=bye.id,
            winner_participant_id=world["p1"].id,
            acting_user_id=world["organizer"].id,
        )


@pytest.mark.asyncio
async def test_manual_result_records_match_win_activity_event(db_session, world):
    """005-US3 instrumentation: a confirmed manual result emits a MATCH_WIN
    activity event for the winning participant's user (research.md Decisión 3)."""
    await match_service.register_manual_result(
        db_session,
        match_id=world["m1"].id,
        winner_participant_id=world["p1"].id,
        acting_user_id=world["organizer"].id,
    )
    events = (
        await db_session.execute(
            select(ActivityFeed).where(ActivityFeed.event_type == "MATCH_WIN")
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].actor_id == world["p1"].user_id
    assert events[0].tournament_id == world["tournament"].id


@pytest.mark.asyncio
async def test_bye_auto_resolution_does_not_record_match_win(db_session, world):
    """A bye that auto-advances its player is NOT a MATCH_WIN event (byes are
    excluded — FR-005/Decisión 3)."""
    tournament = world["tournament"]
    bye = Match(
        tournament_id=tournament.id,
        round_number=1,
        bracket_position=2,
        player1_id=world["p1"].id,
        player2_id=None,
        is_bye=True,
        tournament_code=None,
        state="pending",
    )
    db_session.add(bye)
    await db_session.flush()
    # Resolve m1 and m2 so the round closes and the bye auto-resolves.
    await match_service.register_manual_result(
        db_session, match_id=world["m1"].id,
        winner_participant_id=world["p1"].id, acting_user_id=world["organizer"].id,
    )
    await match_service.register_manual_result(
        db_session, match_id=world["m2"].id,
        winner_participant_id=world["p3"].id, acting_user_id=world["organizer"].id,
    )
    # No MATCH_WIN event should reference the bye's auto-advance specifically;
    # only the two real wins above are recorded.
    events = (
        await db_session.execute(
            select(ActivityFeed).where(ActivityFeed.event_type == "MATCH_WIN")
        )
    ).scalars().all()
    assert len(events) == 2


@pytest.mark.asyncio
async def test_round_robin_last_result_transitions_tournament_to_finished(db_session):
    """In round-robin, the last pending match resolves -> tournament finished."""
    make = _user_factory(db_session)
    ua, ub = await make("a@x.com", "Aa"), await make("b@x.com", "Bb")
    organizer = await make("org@x.com", "Orgrr")

    tournament = Tournament(
        name="RR", format="round_robin", state="active", organizer_id=organizer.id
    )
    db_session.add(tournament)
    await db_session.flush()
    pa = Participant(tournament_id=tournament.id, user_id=ua.id)
    pb = Participant(tournament_id=tournament.id, user_id=ub.id)
    db_session.add(pa)
    db_session.add(pb)
    await db_session.flush()

    m = Match(
        tournament_id=tournament.id,
        round_number=1,
        player1_id=pa.id,
        player2_id=pb.id,
        is_bye=False,
        tournament_code="tc-rr",
        state="pending",
    )
    db_session.add(m)
    await db_session.flush()

    await match_service.register_manual_result(
        db_session,
        match_id=m.id,
        winner_participant_id=pa.id,
        acting_user_id=organizer.id,
    )
    await db_session.refresh(tournament)
    assert tournament.state == "finished"
