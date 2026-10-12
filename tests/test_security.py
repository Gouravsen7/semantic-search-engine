"""Password hashing and access tokens."""

from uuid import uuid4

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_verifies_the_same_password_only():
    stored = hash_password("password12")

    assert stored != "password12"
    assert verify_password("password12", stored)
    assert not verify_password("password13", stored)


def test_access_token_round_trip():
    user_id = uuid4()
    token = create_access_token(user_id, "test-secret", expire_minutes=15)
    assert decode_access_token(token, "test-secret") == user_id


def test_access_token_rejects_a_bad_token():
    user_id = uuid4()
    token = create_access_token(user_id, "test-secret", expire_minutes=15)
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered, "test-secret")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, "other-secret")

    expired = create_access_token(user_id, "test-secret", expire_minutes=-1)
    with pytest.raises(InvalidTokenError):
        decode_access_token(expired, "test-secret")
