"""
Security utilities for hardening the application.
Includes CORS restrictions, security headers, and validators.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (strict)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' https:; "
            "font-src 'self'; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # HSTS (HTTP Strict-Transport-Security)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Feature Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Remove server identification
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase
    - At least one lowercase
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\",.<>?/]", password):
        return False, "Password must contain at least one special character"
    
    return True, None


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input.
    Remove potentially dangerous characters.
    """
    if len(value) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length}")
    
    # Remove null bytes
    value = value.replace("\x00", "")
    
    # Remove control characters
    value = "".join(char for char in value if ord(char) >= 32 or char in "\n\r\t")
    
    return value.strip()


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe."""
    # Allow only alphanumeric, dots, hyphens, and underscores
    pattern = r"^[a-zA-Z0-9._-]+$"
    return re.match(pattern, filename) is not None


class OriginValidator:
    """Validate CORS origins based on environment."""
    
    def __init__(self, allowed_origins: list[str]):
        self.allowed_origins = allowed_origins
        self.origin_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> list[re.Pattern]:
        """Compile origin patterns for matching."""
        patterns = []
        for origin in self.allowed_origins:
            if "*" in origin:
                # Convert wildcard to regex
                pattern = origin.replace(".", r"\.").replace("*", ".*")
                patterns.append(re.compile(f"^{pattern}$"))
            else:
                patterns.append(origin)
        return patterns
    
    def is_valid(self, origin: Optional[str]) -> bool:
        """Check if origin is valid."""
        if not origin:
            return False
        
        for allowed in self.origin_patterns:
            if isinstance(allowed, str):
                if origin == allowed:
                    return True
            else:
                if allowed.match(origin):
                    return True
        
        return False
    
    def log_invalid_origin(self, origin: str, path: str):
        """Log suspicious origin attempts."""
        logger.warning(
            "Invalid CORS origin attempt",
            extra={
                "origin": origin,
                "path": path,
                "severity": "medium",
            }
        )


def check_sql_injection(query: str) -> bool:
    """
    Basic SQL injection detection.
    NOTE: Use parameterized queries (SQLAlchemy ORM) as primary defense.
    """
    dangerous_patterns = [
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|/\*|\*/)",
        r"(;|\||&&)",
    ]
    
    query_upper = query.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, query_upper):
            return False  # Potential injection
    
    return True


def check_xss_payload(value: str) -> bool:
    """
    Basic XSS detection.
    NOTE: Use proper HTML escaping/sanitization as primary defense.
    """
    dangerous_patterns = [
        r"<\s*script[^>]*>.*?</\s*script\s*>",
        r"on\w+\s*=",
        r"javascript:",
        r"<\s*iframe",
        r"<\s*embed",
        r"<\s*object",
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return False  # Potential XSS
    
    return True
