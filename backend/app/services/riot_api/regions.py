"""Riot region mapping.

`region` (platform) is what the user picks at link time and what we persist
in `riot_accounts.region`. Platforms host the per-summoner endpoints
(champion-mastery/v4, league/v4, summoner/v4). `continent` is what
account/v1 lives on (americas / europe / asia) — derived deterministically
from the platform.
"""
from __future__ import annotations

from typing import Literal

# Whitelist of platforms exposed in the link form. Stored uppercase, lowercased
# only when building the API URL host.
PlatformRegion = Literal[
    "EUW1", "EUN1", "TR1", "RU",
    "NA1", "BR1", "LA1", "LA2", "OC1",
    "KR", "JP1",
]

PLATFORMS: tuple[str, ...] = (
    "EUW1", "EUN1", "TR1", "RU",
    "NA1", "BR1", "LA1", "LA2", "OC1",
    "KR", "JP1",
)

_PLATFORM_TO_CONTINENT: dict[str, str] = {
    "EUW1": "europe",
    "EUN1": "europe",
    "TR1": "europe",
    "RU": "europe",
    "NA1": "americas",
    "BR1": "americas",
    "LA1": "americas",
    "LA2": "americas",
    "OC1": "americas",
    "KR": "asia",
    "JP1": "asia",
}


def platform_to_continent(platform: str) -> str:
    """Return the account/v1 continent (americas / europe / asia) for `platform`.

    Raises ValueError if `platform` is not in the supported whitelist.
    """
    try:
        return _PLATFORM_TO_CONTINENT[platform]
    except KeyError as exc:
        raise ValueError(f"Unsupported platform region: {platform!r}") from exc
