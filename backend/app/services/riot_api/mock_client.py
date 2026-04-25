"""MockRiotAPIClient — fixture-driven implementation for tests and local dev.

Used automatically by get_riot_api_client() when RIOT_API_KEY is not set.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.riot_api.client import MatchResult


@dataclass
class MockRiotAPIClient:
    """Returns configured data for deterministic tests.

    Tests populate `configured_match_results` (tournament_code -> MatchResult)
    and `configured_riot_ids` ((game_name, tag_line) tuples that should validate).
    """

    configured_match_results: dict[str, MatchResult] = field(default_factory=dict)
    configured_riot_ids: set[tuple[str, str]] = field(default_factory=set)

    def validate_riot_id(self, game_name: str, tag_line: str) -> bool:
        return (game_name, tag_line) in self.configured_riot_ids

    def get_match_by_tournament_code(self, tournament_code: str) -> MatchResult | None:
        return self.configured_match_results.get(tournament_code)
