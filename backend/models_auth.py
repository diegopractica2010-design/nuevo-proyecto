from pydantic import BaseModel, field_validator
import re
from typing import Any

_SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{}|;:,.<>?"


def validate_password_strength(v: str) -> list[str]:
    """Return list of unmet password requirements (empty = valid)."""
    failures: list[str] = []
    if len(v) < 12:
        failures.append("mínimo 12 caracteres")
    if len(v) > 128:
        failures.append("máximo 128 caracteres")
    if not re.search(r"[A-Z]", v):
        failures.append("al menos 1 letra mayúscula [A-Z]")
    if not re.search(r"[0-9]", v):
        failures.append("al menos 1 dígito [0-9]")
    if not re.search(rf"[{_SPECIAL_CHARS}]", v):
        failures.append(r"al menos 1 carácter especial (!@#$%^&*()_+-=[]{}|;:,.<>?)")
    return failures


class EmailStr(str):
    """Email validation type."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Debe ser una cadena de texto")
        v = v.strip().lower()
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Email inválido")
        return v


class UserCreate(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username debe tener al menos 3 caracteres")
        if len(v) > 80:
            raise ValueError("Username no puede exceder 80 caracteres")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username solo puede contener letras, números, guiones y guión bajo")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Email inválido")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        failures = validate_password_strength(v)
        if failures:
            raise ValueError("; ".join(failures))
        return v


class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username es requerido")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password es requerido")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    username: str
    email: str