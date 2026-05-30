from __future__ import annotations

import os
import secrets
import logging
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.db import SessionLocal
from backend.infrastructure.db.models import UserRecord
from backend.infrastructure.cache.cache import _get_client
from backend.repositories import UserRepository

logger = logging.getLogger(__name__)


def send_verification_email(username: str, email: str, token: str) -> None:
    """Send verification email. In development, only log the URL."""
    import os
    import smtplib
    from email.mime.text import MIMEText

    base_url = os.getenv("BASE_URL", "http://localhost:8001")
    verify_url = f"{base_url}/auth/verify?token={token}"
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "development":
        logger.info("DEV — email verification URL for %s: %s", username, verify_url)
        return

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    body = f"Hola {username},\n\nVerifica tu cuenta aquí:\n{verify_url}\n\nEste enlace expira en 24 horas."
    msg = MIMEText(body)
    msg["Subject"] = "Verifica tu cuenta — Radar de Precios"
    msg["From"] = smtp_from
    msg["To"] = email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", email, exc)


def revoke_token(jti: str, ttl_seconds: int) -> None:
    """Write jti to Redis blacklist so the token cannot be reused after logout."""
    try:
        client = _get_client()
        client.set(f"jwt:blacklist:{jti}", "1", ex=ttl_seconds)
    except Exception as exc:
        logger.warning("Failed to revoke token jti=%s: %s", jti, exc)


def is_token_revoked(jti: str) -> bool:
    """Return True if the jti has been revoked (exists in Redis blacklist)."""
    try:
        import redis as _redis_module
        client = _get_client()
        return client.exists(f"jwt:blacklist:{jti}") > 0
    except (_redis_module.exceptions.ConnectionError, _redis_module.exceptions.TimeoutError):
        # Redis unavailable — assume token is valid (fail-open for availability)
        return False
    except Exception as exc:
        logger.warning("Failed to check token revocation jti=%s: %s", jti, exc)
        return False


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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


class TokenService:
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "iat": datetime.now(UTC), "jti": uuid4().hex})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            jti: str = payload.get("jti", "")
            if jti and is_token_revoked(jti):
                return None
            return username
        except JWTError:
            return None

    @staticmethod
    def decode_payload(token: str) -> Optional[dict]:
        """Decode without blacklist check — used only by logout to extract jti."""
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            return None
