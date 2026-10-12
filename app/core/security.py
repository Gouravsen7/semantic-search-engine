"""Password hashes and HMAC access tokens."""

import base64
import hashlib
import hmac
import json
import os
import time
from uuid import UUID

_ITERATIONS = 200_000


class InvalidTokenError(Exception):
    """The access token is missing, altered, or expired."""


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        expected = bytes.fromhex(digest_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _ITERATIONS)
    except ValueError:
        return False
    return hmac.compare_digest(digest, expected)


def create_access_token(user_id: UUID, secret: str, expire_minutes: int) -> str:
    header = _b64({"alg": "HS256", "typ": "JWT"})
    payload = _b64({"sub": str(user_id), "exp": int(time.time()) + expire_minutes * 60})
    return f"{header}.{payload}.{_sign(f'{header}.{payload}', secret)}"


def decode_access_token(token: str, secret: str) -> UUID:
    try:
        header, payload, signature = token.split(".")
        expected = _sign(f"{header}.{payload}", secret)
        if not hmac.compare_digest(signature, expected):
            raise InvalidTokenError("Invalid or expired token.")
        body = json.loads(_b64decode(payload))
        if int(body["exp"]) <= time.time():
            raise InvalidTokenError("Invalid or expired token.")
        return UUID(body["sub"])
    except (InvalidTokenError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise InvalidTokenError("Invalid or expired token.") from exc


def _b64(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _sign(message: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
