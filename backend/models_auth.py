from pydantic import BaseModel, field_validator
import re
from typing import Any

PASSWORD_SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


def validate_password_strength(password: str) -> list[str]:
    """Return every unmet password policy requirement."""
    failures: list[str] = []
    if len(password) < 12:
        failures.append("be at least 12 characters")
    if len(password) > 128:
        failures.append("be at most 128 characters")
    if not re.search(r"[A-Z]", password):
        failures.append("contain an uppercase letter")
    if not re.search(r"\d", password):
        failures.append("contain a number")
    if not any(char in PASSWORD_SPECIAL_CHARS for char in password):
        failures.append(f"contain a special character ({PASSWORD_SPECIAL_CHARS})")
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
            message = "Password must:\n" + "\n".join(f"- {failure}" for failure in failures)
            raise ValueError(message)
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
    is_verified: bool = False


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Email inválido")
        return v


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        failures = validate_password_strength(v)
        if failures:
            message = "Password must:\n" + "\n".join(f"- {failure}" for failure in failures)
            raise ValueError(message)
        return v
