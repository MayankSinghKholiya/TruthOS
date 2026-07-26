"""Password hashing, JWT issuance/verification, and API-key generation."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

API_KEY_PREFIX = "toc_"  # TruthOS Court


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    return _create_token(
        str(user_id),
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "access",
    )


def create_refresh_token(user_id: UUID) -> str:
    settings = get_settings()
    return _create_token(
        str(user_id),
        timedelta(days=settings.jwt_refresh_token_expire_days),
        "refresh",
    )


def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_hash, key_prefix). The raw key is shown to the
    caller exactly once; only the hash is persisted. Unlike passwords, API
    keys are high-entropy random tokens (256 bits from token_urlsafe(32)), so
    a fast deterministic hash is correct here - it needs to support an exact-
    match lookup by hash, which bcrypt's per-hash random salt makes
    impossible, and the key's own entropy already rules out precomputation
    attacks that salting would otherwise defend against."""
    raw_key = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[: len(API_KEY_PREFIX) + 8]
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def decode_token(token: str, *, expected_type: str = "access") -> str:
    """Return the subject (user id) encoded in the token, or raise UnauthorizedError."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type")

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Malformed token")
    return subject
