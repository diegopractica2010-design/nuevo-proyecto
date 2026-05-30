from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.db import SessionLocal
from backend.infrastructure.cache.cache import (
    cache_delete,
    cache_get,
    cache_set,
    is_token_revoked,
    revoke_token,
)
from backend.infrastructure.db.models import UserRecord
from backend.repositories import UserRepository

logger = logging.getLogger(__name__)


def _get_secret_key() -> str:
    """Obtener JWT_SECRET_KEY desde entorno o generar una temporal en desarrollo."""
    secret = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
    if secret:
        if len(secret) < 32:
            raise ValueError("JWT_SECRET_KEY debe tener al menos 32 caracteres")
        logger.info("JWT_SECRET_KEY configured and fixed (from environment)")
        return secret

    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        raise RuntimeError(
            "JWT_SECRET_KEY no esta configurado. "
            "El servidor no puede arrancar en produccion sin una clave JWT fija. "
            "Agrega JWT_SECRET_KEY al entorno."
        )

    secret = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET_KEY not configured in development. Using ephemeral key. "
        "Tokens will be invalid after server restart. This is only acceptable for development."
    )
    return secret


SECRET_KEY = _get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
EMAIL_VERIFY_EXPIRE_HOURS = 24
PASSWORD_RESET_EXPIRE_SECONDS = 3600

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_admin(authorization: Optional[str] = Header(None, description="Bearer JWT")) -> str:
    """FastAPI dependency — raises 403 if the authenticated user is not an admin."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    username = TokenService.verify_token(authorization[7:])
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = AuthService.get_user(username)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return username


class AuthService:
    @staticmethod
    def create_user(username: str, email: str, password: str) -> UserRecord:
        with SessionLocal() as session:
            users = UserRepository(session)
            if users.get_by_username(username):
                raise ValueError("Username already exists")
            if users.get_by_email(email):
                raise ValueError("Email already exists")

            user = users.create(username, email, pwd_context.hash(password))
            user.is_verified = False
            session.commit()
            session.refresh(user)
            return user

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[UserRecord]:
        with SessionLocal() as session:
            user = UserRepository(session).get_by_username(username)
            if not user:
                return None
            if not pwd_context.verify(password, user.hashed_password):
                return None
            session.expunge(user)
            return user

    @staticmethod
    def get_user(username: str) -> Optional[UserRecord]:
        with SessionLocal() as session:
            user = UserRepository(session).get_by_username(username)
            if user:
                session.expunge(user)
            return user

    @staticmethod
    def verify_email(username: str) -> bool:
        with SessionLocal() as session:
            user = UserRepository(session).get_by_username(username)
            if not user:
                return False
            user.is_verified = True
            session.commit()
            return True

    @staticmethod
    def get_user_by_email(email: str) -> Optional[UserRecord]:
        with SessionLocal() as session:
            user = UserRepository(session).get_by_email(email)
            if user:
                session.expunge(user)
            return user

    @staticmethod
    def update_password(username: str, new_password: str) -> bool:
        with SessionLocal() as session:
            user = UserRepository(session).get_by_username(username)
            if not user:
                return False
            user.hashed_password = pwd_context.hash(new_password)
            session.commit()
            return True


class TokenService:
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update(
            {"exp": expire, "iat": datetime.now(UTC), "jti": uuid4().hex, "purpose": "access"}
        )
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_email_verification_token(username: str) -> str:
        payload = {
            "sub": username,
            "purpose": "email_verify",
            "exp": datetime.now(UTC) + timedelta(hours=EMAIL_VERIFY_EXPIRE_HOURS),
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def create_password_reset_token(username: str) -> str:
        payload = {
            "sub": username,
            "purpose": "pwd_reset",
            "exp": datetime.now(UTC) + timedelta(seconds=PASSWORD_RESET_EXPIRE_SECONDS),
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("purpose") != "access":
                return None
            jti = payload.get("jti")
            if not jti or is_token_revoked(jti):
                raise HTTPException(status_code=401, detail="Invalid token")
            username: str = payload.get("sub")
            if username is None:
                return None
            user = AuthService.get_user(username)
            if not user:
                return None
            if not user.is_verified:
                raise HTTPException(status_code=403, detail="Email not verified")
            return username
        except HTTPException:
            raise
        except JWTError:
            return None

    @staticmethod
    def revoke_access_token(token: str) -> None:
        payload = TokenService.decode_token(token)
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token")
        ttl_seconds = TokenService.remaining_ttl_seconds(payload)
        if ttl_seconds > 0:
            revoke_token(jti, ttl_seconds)

    @staticmethod
    def remaining_ttl_seconds(payload: dict) -> int:
        exp = payload.get("exp")
        if exp is None:
            return 0
        return max(0, int(exp - datetime.now(UTC).timestamp()))

    @staticmethod
    def store_password_reset_token(username: str, token: str) -> None:
        cache_set(f"pwd_reset:{username}", hash_token(token), ttl=PASSWORD_RESET_EXPIRE_SECONDS)

    @staticmethod
    def password_reset_token_matches(username: str, token: str) -> bool:
        return cache_get(f"pwd_reset:{username}") == hash_token(token)

    @staticmethod
    def delete_password_reset_token(username: str) -> None:
        cache_delete(f"pwd_reset:{username}")
