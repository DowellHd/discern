"""JWT authentication helpers and FastAPI dependencies.

Token lifecycle:
  POST /auth/register  → create account, return token
  POST /auth/login     → verify password, return token
  GET  /auth/me        → return current user

Demo mode (DISCERN_DEMO_MODE=true):
  All endpoints accept requests with no token. A shared demo user is used
  transparently — callers never need to register or log in.

Encryption:
  Sensitive field values are Fernet-encrypted at rest when
  DISCERN_FIELD_ENCRYPTION_KEY is set (32-byte URL-safe base64 key).
  Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from discern.api.deps import get_db
from discern.config import settings
from discern.db.models import User

log = structlog.get_logger()

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 30

_DEMO_EMAIL = "demo@discern.local"
_DEMO_USER_ID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _secret() -> str:
    key = settings.jwt_secret
    if not key:
        raise RuntimeError("DISCERN_JWT_SECRET is not set")
    return key


def create_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "exp": expire}, _secret(), algorithm=_ALGORITHM)


def _decode_token(token: str) -> str:
    """Return user_id from a valid token, or raise 401."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
        uid = payload.get("sub")
        if not uid:
            raise ValueError("no sub")
        return str(uid)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


# ---------------------------------------------------------------------------
# Demo user bootstrap
# ---------------------------------------------------------------------------


def _ensure_demo_user(db: Session) -> User:
    user = db.get(User, _DEMO_USER_ID)
    if user is None:
        user = User(
            id=_DEMO_USER_ID,
            email=_DEMO_EMAIL,
            hashed_password=hash_password(os.urandom(32).hex()),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from Bearer token, or demo user if demo mode is on."""
    if settings.demo_mode:
        return _ensure_demo_user(db)

    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    uid = _decode_token(creds.credentials)
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Encryption at rest (Fernet, optional)
# ---------------------------------------------------------------------------


def _fernet() -> object | None:
    key = settings.field_encryption_key
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet

        return Fernet(key.encode())
    except Exception as exc:
        log.warning("fernet_init_error", error=str(exc))
        return None


_fernet_instance = None
_fernet_checked = False


def _get_fernet() -> object | None:
    global _fernet_instance, _fernet_checked
    if not _fernet_checked:
        _fernet_instance = _fernet()
        _fernet_checked = True
    return _fernet_instance


def encrypt_field(value: str) -> str:
    """Encrypt a sensitive field value. Returns plaintext if no key is configured."""
    f = _get_fernet()
    if f is None:
        return value
    return f.encrypt(value.encode()).decode()  # type: ignore[union-attr]


def decrypt_field(value: str) -> str:
    """Decrypt a sensitive field value. Returns value as-is if no key is configured."""
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()  # type: ignore[union-attr]
    except Exception:
        return value
