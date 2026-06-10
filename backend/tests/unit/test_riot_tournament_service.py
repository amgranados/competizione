"""Unit tests for riot_tournament_service (Tournament-Stub-V5 provisioning)."""
from __future__ import annotations

import pytest
import pytest_asyncio

from app.models.match import Match
from app.models.participant import Participant
from app.models.riot_account import RiotAccount
from app.models.tournament import Tournament
from app.models.user import User
from app.services import riot_tournament_service
from app.services.riot_api.mock_client import MockRiotAPIClient


@pytest_asyncio.fixture
async def world(db_session):
    """Tournament with 2 riot-linked participants and one pending match
    carrying a local fallback code."""
    users = []
    for tag in ("a", "b", "org"):
        user = User(email=f"{tag}@x.com", nickname=f"U{tag}", password_hash="x")
        db_session.add(user)
        users.append(user)
    await db_session.flush()
    u1, u2, organizer = users

    for user in (u1, u2):
        db_session.add(
            RiotAccount(
                user_id=user.id,
                puuid=f"puuid-{user.nickname}",
                game_name=user.nickname,
                tag_line="EUW",
                region="EUW1",
            )
        )

    tournament = Tournament(
        name="Copa Stub", format="round_robin", state="active", organizer_id=organizer.id
    )
    db_session.add(tournament)
    await db_session.flush()

    p1 = Participant(tournament_id=tournament.id, user_id=u1.id)
    p2 = Participant(tournament_id=tournament.id, user_id=u2.id)
    db_session.add_all([p1, p2])
    await db_session.flush()

    match = Match(
        tournament_id=tournament.id,
        round_number=1,
        player1_id=p1.id,
        player2_id=p2.id,
        is_bye=False,
        tournament_code="local-fallback-code",
        state="pending",
    )
    bye = Match(
        tournament_id=tournament.id,
        round_number=1,
        player1_id=p1.id,
        player2_id=None,
        is_bye=True,
        tournament_code=None,
        state="pending",
    )
    db_session.add_all([match, bye])
    await db_session.flush()
    return {"tournament": tournament, "match": match, "bye": bye, "p1": p1, "p2": p2}


@pytest.mark.asyncio
async def test_provision_registers_tournament_and_assigns_codes(db_session, world):
    client = MockRiotAPIClient()
    tournament, match, bye = world["tournament"], world["match"], world["bye"]

    await riot_tournament_service.provision_codes(
        db_session, tournament, [match, bye], client=client
    )

    # Provider + tournament registered once, ids persisted.
    assert tournament.riot_provider_id == 100
    assert tournament.riot_tournament_id == 1000
    assert len(client.created_providers) == 1
    assert len(client.created_tournaments) == 1
    assert client.created_tournaments[0]["name"] == "Copa Stub"

    # One code per real match (the bye gets none), restricted to both puuids
    # and correlated with the internal match id via metadata.
    assert len(client.created_codes) == 1
    issued = client.created_codes[0]
    assert match.tournament_code == issued["code"]
    assert issued["team_size"] == 1
    assert sorted(issued["allowed_puuids"]) == ["puuid-Ua", "puuid-Ub"]
    assert issued["metadata"] == str(match.id)
    assert bye.tournament_code is None


@pytest.mark.asyncio
async def test_provision_reuses_existing_riot_tournament(db_session, world):
    client = MockRiotAPIClient()
    tournament, match = world["tournament"], world["match"]
    tournament.riot_provider_id = 7
    tournament.riot_tournament_id = 77

    await riot_tournament_service.provision_codes(
        db_session, tournament, [match], client=client
    )

    # No re-registration: codes are requested against the stored id.
    assert client.created_providers == []
    assert client.created_tournaments == []
    assert tournament.riot_tournament_id == 77
    assert client.created_codes[0]["tournament_id"] == 77


@pytest.mark.asyncio
async def test_provision_falls_back_to_local_codes_when_riot_unavailable(
    db_session, world
):
    client = MockRiotAPIClient(stub_unavailable=True)
    tournament, match = world["tournament"], world["match"]

    await riot_tournament_service.provision_codes(
        db_session, tournament, [match], client=client
    )

    # No exception propagated; the local fallback code is preserved.
    assert match.tournament_code == "local-fallback-code"
    assert tournament.riot_tournament_id is None
