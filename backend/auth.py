from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import REQUEST_TIMEOUT


# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User:
    def __init__(self, username: str, email: str, hashed_password: str):
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.created_at = datetime.now()
        self.is_active = True


# Almacenamiento en memoria (para desarrollo)
_USERS: dict[str, User] = {}


class AuthService:
    @staticmethod
    def create_user(username: str, email: str, password: str) -> User:
        if username in _USERS:
            raise ValueError("Username already exists")

        hashed_password = pwd_context.hash(password)
        user = User(username, email, hashed_password)
        _USERS[username] = user
        return user

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        user = _USERS.get(username)
        if not user:
            return None
        if not pwd_context.verify(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def get_user(username: str) -> Optional[User]:
        return _USERS.get(username)


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