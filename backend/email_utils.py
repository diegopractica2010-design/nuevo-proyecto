from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from backend.config import ENVIRONMENT, SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

logger = logging.getLogger(__name__)


async def send_verification_email(to_email: str, verification_url: str) -> None:
    await _send_auth_email(
        to_email=to_email,
        subject="Verify your Radar de Precios account",
        body=(
            "Welcome to Radar de Precios.\n\n"
            "Verify your email address with this link:\n"
            f"{verification_url}\n\n"
            "This link expires in 24 hours."
        ),
        development_log_url=verification_url,
    )


async def send_password_reset_email(to_email: str, reset_url: str) -> None:
    await _send_auth_email(
        to_email=to_email,
        subject="Reset your Radar de Precios password",
        body=(
            "A password reset was requested for your Radar de Precios account.\n\n"
            "Reset your password with this link:\n"
            f"{reset_url}\n\n"
            "This link expires in 1 hour. If you did not request it, ignore this email."
        ),
        development_log_url=reset_url,
    )


async def _send_auth_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    development_log_url: str,
) -> None:
    if ENVIRONMENT in {"development", "test"}:
        logger.info("Development auth email URL for %s: %s", to_email, development_log_url)
        return

    if not SMTP_HOST:
        logger.warning("SMTP_HOST is not configured; auth email to %s was not sent", to_email)
        return

    await asyncio.to_thread(_send_smtp_email, to_email, subject, body)


def _send_smtp_email(to_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM or SMTP_USER
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)
