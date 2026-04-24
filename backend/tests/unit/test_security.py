import time
from datetime import timedelta

import jwt
import pytest

from app.core import security


def test_hash_password_is_not_reversible():
    hashed = security.hash_password("hunter2-abc")
    assert hashed != "hunter2-abc"
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$") or hashed.startswith("$2y$")


def test_verify_password_accepts_correct_and_rejects_incorrect():
    hashed = security.hash_password("hunter2-abc")
    assert security.verify_password("hunter2-abc", hashed) is True
    assert security.verify_password("wrong", hashed) is False


def test_dummy_verify_runs_in_comparable_time():
    real_hash = security.hash_password("hunter2-abc")
    start = time.perf_counter()
    security.verify_password("wrong-password", real_hash)
    real_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    security.dummy_verify()
    dummy_elapsed = time.perf_counter() - start

    # Within an order of magnitude — both should be doing a real bcrypt verify.
    assert dummy_elapsed > real_elapsed / 10
    assert dummy_elapsed < real_elapsed * 10


def test_create_access_token_encodes_hs256_with_type_access():
    token, _ = security.create_access_token(subject="user-123")
    decoded = jwt.decode(token, security.get_secret(), algorithms=["HS256"])
    assert decoded["sub"] == "user-123"
    assert decoded["type"] == "access"
    assert "exp" in decoded
    assert "iat" in decoded


def test_create_refresh_token_includes_jti_and_type_refresh():
    token, jti = security.create_refresh_token(subject="user-123")
    decoded = jwt.decode(token, security.get_secret(), algorithms=["HS256"])
    assert decoded["type"] == "refresh"
    assert decoded["jti"] == jti
    assert "exp" in decoded


def test_verify_token_accepts_valid_access_token():
    token, _ = security.create_access_token(subject="user-123")
    payload = security.verify_token(token, expected_type="access")
    assert payload["sub"] == "user-123"


def test_verify_token_rejects_wrong_type():
    access_token, _ = security.create_access_token(subject="user-123")
    with pytest.raises(security.InvalidToken):
        security.verify_token(access_token, expected_type="refresh")


def test_verify_token_rejects_alg_none():
    forged = jwt.encode({"sub": "attacker", "type": "access"}, "", algorithm="none")
    with pytest.raises(security.InvalidToken):
        security.verify_token(forged, expected_type="access")


def test_verify_token_rejects_expired_token():
    token, _ = security.create_access_token(subject="user-123", expires_delta=timedelta(seconds=-1))
    with pytest.raises(security.InvalidToken):
        security.verify_token(token, expected_type="access")


def test_verify_token_rejects_tampered_signature():
    token, _ = security.create_access_token(subject="user-123")
    tampered = token[:-4] + "AAAA"
    with pytest.raises(security.InvalidToken):
        security.verify_token(tampered, expected_type="access")
