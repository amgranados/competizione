"""Provisión de torneos en Riot vía Tournament-Stub-V5.

Flujo de la Tournament API de Riot (el stub es su sandbox 1:1):

1. ``POST /providers``  → providerId. Registra la app como organizadora de
   torneos en una región, con una callback URL a la que Riot enviaría el
   resultado de cada partida jugada con un código.
2. ``POST /tournaments`` → tournamentId. Contenedor lógico bajo el provider.
3. ``POST /codes``       → códigos de partida. Cada código se introduce en el
   cliente de LoL y crea la lobby con las reglas pedidas (mapa, modo de picks,
   tamaño de equipo, jugadores permitidos…).

Este módulo se invoca al arrancar un torneo y al generarse cada nueva ronda de
eliminación directa: registra el torneo en Riot (una vez) y pide un código por
partida, restringido a los PUUID de los dos jugadores. Si Riot no está
disponible, las partidas conservan el código local generado por
``calendar_service`` — el torneo nunca se bloquea por la integración.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.match import Match
from app.models.participant import Participant
from app.models.riot_account import RiotAccount
from app.models.tournament import Tournament
from app.services.riot_api.client import (
    RiotIdentityError,
    RiotUnavailableError,
    get_riot_api_client,
)

logger = logging.getLogger(__name__)

# Las partidas de competizione son 1v1.
_TEAM_SIZE = 1


async def _puuids_by_participant(
    session: AsyncSession, tournament_id: uuid.UUID
) -> dict[uuid.UUID, str]:
    """participant.id → puuid de la cuenta Riot vinculada de su usuario."""
    stmt = (
        select(Participant.id, RiotAccount.puuid)
        .join(RiotAccount, RiotAccount.user_id == Participant.user_id)
        .where(Participant.tournament_id == tournament_id)
    )
    rows = (await session.execute(stmt)).all()
    return {participant_id: puuid for participant_id, puuid in rows}


async def _ensure_registered(tournament: Tournament, client, settings) -> None:
    """Registra provider + torneo en Riot la primera vez (ids persistidos)."""
    if tournament.riot_tournament_id is not None:
        return
    provider_id = await client.create_tournament_provider(
        settings.RIOT_TOURNAMENT_REGION, settings.RIOT_TOURNAMENT_CALLBACK_URL
    )
    riot_tournament_id = await client.create_tournament(provider_id, tournament.name)
    tournament.riot_provider_id = provider_id
    tournament.riot_tournament_id = riot_tournament_id


async def provision_codes(
    session: AsyncSession,
    tournament: Tournament,
    matches: list[Match],
    *,
    client=None,
) -> None:
    """Sustituye los códigos locales de `matches` por códigos reales de Riot.

    Un código por partida (no-bye), restringido a los PUUID de ambos
    jugadores cuando se conocen, con el id interno de la Match como
    `metadata` para correlacionar el callback de resultados. Cualquier fallo
    de Riot deja los códigos locales y no propaga la excepción.
    """
    real_matches = [m for m in matches if not m.is_bye]
    if not real_matches:
        return

    settings = get_settings()
    if client is None:
        client = get_riot_api_client(settings)

    try:
        await _ensure_registered(tournament, client, settings)
        puuids = await _puuids_by_participant(session, tournament.id)
        for match in real_matches:
            allowed = [
                p
                for p in (puuids.get(match.player1_id), puuids.get(match.player2_id))
                if p is not None
            ]
            codes = await client.create_tournament_codes(
                tournament.riot_tournament_id,
                1,
                team_size=_TEAM_SIZE,
                allowed_puuids=allowed if len(allowed) == 2 else None,
                metadata=str(match.id),
            )
            if codes:
                # El modelo limita el código a 64 caracteres.
                match.tournament_code = codes[0][:64]
        await session.flush()
    except (RiotIdentityError, RiotUnavailableError) as exc:
        logger.warning(
            "Tournament-Stub-V5 no disponible (%s); el torneo %s mantiene "
            "códigos locales de respaldo",
            exc,
            tournament.id,
        )
