"""Unit tests for Pydantic schemas (003-edit-profile)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.profile import (
    DeleteAccountConfirm,
    LinkRiotAccount,
    UpdateAvatar,
    UpdateNickname,
    UpdatePassword,
)


def test_update_avatar_accepts_https_url():
    schema = UpdateAvatar(avatar_url="https://i.imgur.com/x.png")
    assert str(schema.avatar_url).startswith("https://i.imgur.com/")


def test_update_avatar_accepts_http_url():
    schema = UpdateAvatar(avatar_url="http://cdn.example.com/photo.jpg")
    assert str(schema.avatar_url).startswith("http://")


def test_update_avatar_rejects_garbage_url():
    with pytest.raises(ValidationError):
        UpdateAvatar(avatar_url="not-a-url")


def test_update_avatar_accepts_null_to_clear():
    schema = UpdateAvatar(avatar_url=None)
    assert schema.avatar_url is None


def test_link_riot_account_validates_region_whitelist():
    # El contrato vigente acepta códigos de PLATAFORMA (EUW1, KR, ...), no
    # continentes. El continente se deriva en el servicio vía platform_to_continent.
    for region in ("EUW1", "KR", "NA1", "LA2", "JP1"):
        schema = LinkRiotAccount(game_name="Faker", tag_line="KR1", region=region)
        assert schema.region == region


def test_link_riot_account_rejects_unknown_region():
    # Continentes y valores arbitrarios ya NO son regiones válidas; sólo plataformas.
    for bad in ("europe", "asia", "americas", "ZZZ", "euw1", "Europe", ""):
        with pytest.raises(ValidationError):
            LinkRiotAccount(game_name="Faker", tag_line="KR1", region=bad)


def test_link_riot_account_requires_all_fields():
    with pytest.raises(ValidationError):
        LinkRiotAccount(game_name="Faker", region="EUW1")  # type: ignore[call-arg]


def test_link_riot_account_rejects_path_and_control_chars():
    # L-02: barras y caracteres de control no son válidos en un Riot ID.
    for bad_name in ("Hide/Bush", "back\\slash", "ctrl\x00char", "tab\tchar"):
        with pytest.raises(ValidationError):
            LinkRiotAccount(game_name=bad_name, tag_line="EUW", region="EUW1")
    for bad_tag in ("EU/W", "x\x1f"):
        with pytest.raises(ValidationError):
            LinkRiotAccount(game_name="Faker", tag_line=bad_tag, region="EUW1")


def test_link_riot_account_allows_spaces_in_name():
    # Los Riot ID admiten espacios; no deben rechazarse.
    schema = LinkRiotAccount(game_name="Hide on bush", tag_line="KR1", region="KR")
    assert schema.game_name == "Hide on bush"


def test_delete_account_confirm_requires_string():
    schema = DeleteAccountConfirm(confirmation="alice")
    assert schema.confirmation == "alice"

    with pytest.raises(ValidationError):
        DeleteAccountConfirm()  # type: ignore[call-arg]


def test_update_nickname_accepts_letters():
    schema = UpdateNickname(nickname="alice")
    assert schema.nickname == "alice"


def test_update_nickname_rejects_empty():
    with pytest.raises(ValidationError):
        UpdateNickname(nickname="")


def test_update_nickname_rejects_too_long():
    with pytest.raises(ValidationError):
        UpdateNickname(nickname="a" * 33)


def test_update_password_requires_min_length():
    schema = UpdatePassword(current_password="oldpass1", new_password="newPass123")
    assert schema.new_password == "newPass123"


def test_update_password_rejects_too_short_new_password():
    with pytest.raises(ValidationError):
        UpdatePassword(current_password="oldpass1", new_password="short")
