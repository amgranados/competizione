"""DDragon client — resolves champion IDs to display names + asset URLs.

DDragon is Riot's static data CDN; no API key needed. The champion catalogue
rarely changes within a patch, so we fetch it once per process and cache the
{championId: {name, image_slug}} mapping in memory. If the fetch fails we
degrade with a synthetic placeholder name and skip the image URL.

Champion image URL: cdn/{VERSION}/img/champion/{slug}.png
Profile icon URL:   cdn/{VERSION}/img/profileicon/{icon_id}.png
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

DDRAGON_VERSION = "16.8.1"
_BASE = f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}"
_CATALOGUE_URL = f"{_BASE}/data/en_US/champion.json"
_TIMEOUT = httpx.Timeout(5.0, connect=3.0)


@dataclass(frozen=True)
class ChampionAsset:
    name: str
    image_url: str


_cache: dict[int, ChampionAsset] | None = None
_lock = asyncio.Lock()


def champion_image_url(slug: str) -> str:
    return f"{_BASE}/img/champion/{slug}.png"


def profile_icon_url(icon_id: int) -> str:
    return f"{_BASE}/img/profileicon/{icon_id}.png"


async def _load() -> dict[int, ChampionAsset]:
    global _cache
    async with _lock:
        if _cache is not None:
            return _cache
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(_CATALOGUE_URL)
            response.raise_for_status()
            data = response.json().get("data", {})
            _cache = {
                int(entry["key"]): ChampionAsset(
                    name=entry["name"],
                    image_url=champion_image_url(entry["id"]),
                )
                for entry in data.values()
            }
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("DDragon champion fetch failed: %s", exc)
            _cache = {}
        return _cache


async def champion_assets(champion_ids: list[int]) -> dict[int, ChampionAsset]:
    catalogue = await _load()
    return {
        cid: catalogue.get(cid, ChampionAsset(name=f"Champion #{cid}", image_url=""))
        for cid in champion_ids
    }
