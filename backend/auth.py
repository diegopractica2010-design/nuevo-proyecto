from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.db import SessionLocal
from backend.db_models import UserRecord
from backend.repositories import UserRepository


def _get_secret_key() -> str:
    """Obtener SECRET_KEY desde entorno o generar una nueva."""
    secret = os.getenv("SECRET_KEY")
    if secret:
        if len(secret) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return secret
    
    # Generar clave segura si no existe (para desarrollo)
    generated = secrets.token_hex(32)
    return generated


SECRET_KEY = _get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except JWTError:
            return None
