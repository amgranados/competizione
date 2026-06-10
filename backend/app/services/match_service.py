"""Match service (US3 — manual results, winner advancement, finalization).

Implements FR-040..FR-046, FR-049, FR-050 and the round-closure/auto-finalize
transitions (FR-020, FR-028).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.participant import Participant
from app.models.tournament import Tournament
from app.services import activity_service, calendar_service, notification_service


class MatchNotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class InvalidState(Exception):
    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_match(session: AsyncSession, match_id: uuid.UUID) -> Match:
    match = await session.get(Match, match_id)
    if match is None:
        raise MatchNotFound()
    return match


async def _all_matches(session: AsyncSession, tournament_id: uuid.UUID) -> list[Match]:
    result = await session.execute(
        select(Match).where(Match.tournament_id == tournament_id).order_by(
            Match.round_number, Match.bracket_position
        )
    )
    return list(result.scalars().all())


async def register_manual_result(
    session: AsyncSession,
    *,
    match_id: uuid.UUID,
    winner_participant_id: uuid.UUID,
    acting_user_id: uuid.UUID,
) -> Match:
    match = await session.get(Match, match_id)
    if match is None:
        raise MatchNotFound()

    tournament = await session.get(Tournament, match.tournament_id)
    if tournament is None:
        raise MatchNotFound()
    if tournament.organizer_id != acting_user_id:
        raise Forbidden()
    if tournament.state != "active":
        raise InvalidState("tournament is not active")
    if match.is_bye:
        raise InvalidState("byes cannot receive a manual result")
    if match.state != "pending":
        raise InvalidState("match already resolved — label is permanent (FR-042)")
    if winner_participant_id not in (match.player1_id, match.player2_id):
        raise InvalidState("winner is not a player of this match")

    match.state = "manual"
    match.winner_participant_id = winner_participant_id
    match.resolved_at = _now()
    await session.flush()

    # Notify both players.
    participants = await _participants_by_id(session, tournament.id)
    for pid in (match.player1_id, match.player2_id):
        p = participants.get(pid)
        if p is not None:
            await notification_service.create_notification(
                session,
                user_id=p.user_id,
                type="match_resolved",
                tournament_id=tournament.id,
                match_id=match.id,
            )

    # 005-US3: record the MATCH_WIN activity event for the winner's user. Byes
    # are excluded above (they never reach here), so this is a real, decided win.
    winner = participants.get(winner_participant_id)
    if winner is not None:
        await activity_service.record(
            session,
            actor_id=winner.user_id,
            event_type="MATCH_WIN",
            tournament_id=tournament.id,
        )

    # Try to close the round / generate the next.
    await _maybe_close_round(session, tournament, match.round_number)
    return match


async def _participants_by_id(
    session: AsyncSession, tournament_id: uuid.UUID
) -> dict[uuid.UUID, Participant]:
    result = await session.execute(
        select(Participant).where(Participant.tournament_id == tournament_id)
    )
    return {p.id: p for p in result.scalars().all()}


async def _maybe_close_round(
    session: AsyncSession, tournament: Tournament, round_number: int
) -> None:
    matches = await _all_matches(session, tournament.id)
    current_round = [m for m in matches if m.round_number == round_number]
    # Resolve byes (auto-advance their single player).
    for m in current_round:
        if m.is_bye and m.state == "pending":
            m.state = "manual"
            m.winner_participant_id = m.player1_id
            m.resolved_at = _now()
    await session.flush()

    current_round = [m for m in matches if m.round_number == round_number]
    # Round closed when all matches are no longer pending.
    all_closed = all(m.state != "pending" for m in current_round)
    if not all_closed:
        return

    if tournament.format == "single_elim":
        # Build winners list in bracket order.
        winners = [
            m.winner_participant_id
            for m in sorted(current_round, key=lambda m: (m.bracket_position or 0))
            if m.winner_participant_id is not None
        ]
        if len(winners) <= 1:
            # Tournament over: finalize with the last winner.
            await _finalize(session, tournament)
            return
        new_round = calendar_service.generate_next_single_elim_round(
            winners, round_number=round_number + 1
        )
        # Persist new round's matches.
        participants = await _participants_by_id(session, tournament.id)
        for m in new_round.matches:
            match = Match(
                tournament_id=tournament.id,
                round_number=m.round_number,
                bracket_position=m.bracket_position,
                player1_id=m.player1_id,
                player2_id=m.player2_id,
                is_bye=m.is_bye,
                tournament_code=m.tournament_code,
                code_created_at=m.code_created_at,
                state="pending",
            )
            session.add(match)
            await session.flush()
            if not m.is_bye:
                for pid in (m.player1_id, m.player2_id):
                    p = participants.get(pid)
                    if p is not None:
                        await notification_service.create_notification(
                            session,
                            user_id=p.user_id,
                            type="match_generated",
                            tournament_id=tournament.id,
                            match_id=match.id,
                        )
        await session.flush()
    else:
        # Round-robin: round 1 contains all matches. When they are all closed,
        # the tournament is finished.
        all_matches = await _all_matches(session, tournament.id)
        if all(m.state != "pending" for m in all_matches):
            await _finalize(session, tournament)


async def _finalize(session: AsyncSession, tournament: Tournament) -> None:
    if tournament.state == "finished":
        return
    tournament.state = "finished"
    tournament.finished_at = _now()
    await session.flush()
    # Notify all active participants (I-05: inserción en bloque).
    result = await session.execute(
        select(Participant).where(
            Participant.tournament_id == tournament.id,
            Participant.removed.is_(False),
        )
    )
    await notification_service.create_notifications_bulk(
        session,
        [
            {
                "user_id": p.user_id,
                "type": "tournament_finished",
                "tournament_id": tournament.id,
            }
            for p in result.scalars().all()
        ],
    )
