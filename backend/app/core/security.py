from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


JWT_ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: UUID, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return _create_token(user_id, "access", expires_at, role=role)


def create_refresh_token(user_id: UUID) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    token = _create_token(user_id, "refresh", expires_at)
    return token, expires_at


def decode_token_subject(token: str, expected_type: TokenType) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "iat", "exp", "jti"]},
        )

        if payload["type"] != expected_type:
            raise InvalidTokenError("Unexpected token type")

        return UUID(payload["sub"])
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidTokenError("Invalid token claims") from error


def hash_refresh_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _create_token(
    user_id: UUID,
    token_type: TokenType,
    expires_at: datetime,
    *,
    role: str | None = None,
) -> str:
    issued_at = datetime.now(timezone.utc)
    payload: dict[str, object] = {
        "sub": str(user_id),
        "type": token_type,
        "iat": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }

    if role is not None:
        payload["role"] = role

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
