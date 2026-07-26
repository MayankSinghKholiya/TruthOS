import uuid

import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    assert decode_token(token, expected_type="access") == str(user_id)


def test_refresh_token_rejected_as_access_token():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    with pytest.raises(UnauthorizedError):
        decode_token(token, expected_type="access")


def test_garbage_token_raises_unauthorized():
    with pytest.raises(UnauthorizedError):
        decode_token("not-a-real-token", expected_type="access")


def test_generate_api_key_hash_matches_lookup_hash():
    raw_key, key_hash, key_prefix = generate_api_key()
    assert raw_key.startswith("toc_")
    assert raw_key.startswith(key_prefix)
    # The whole point of hashing API keys with SHA-256 instead of bcrypt is
    # that hashing the same raw key twice must always produce the same
    # digest, so a DB lookup by exact hash match is possible.
    assert hash_api_key(raw_key) == key_hash


def test_generate_api_key_is_unique_per_call():
    first_key, _, _ = generate_api_key()
    second_key, _, _ = generate_api_key()
    assert first_key != second_key
