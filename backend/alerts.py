"""
Alerting system for critical events.
Supports Slack, email, and PagerDuty notifications.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Optional

import httpx
from datetime import datetime, UTC

from backend.config import (
    SLACK_WEBHOOK_URL,
    SLACK_CHANNEL,
    PAGERDUTY_INTEGRATION_KEY,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM,
    ALERT_EMAIL_RECIPIENTS,
)

logger = logging.getLogger(__name__)


class AlertLevel:
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertManager:
    """Manage alerts and notifications."""
    
    @staticmethod
    async def send_slack_alert(
        message: str,
        title: str,
        level: str = AlertLevel.INFO,
        additional_info: Optional[dict] = None,
    ) -> bool:
        """
        Send alert to Slack.
        
        Args:
            message: Alert message body
            title: Alert title
            level: Alert level (info, warning, critical)
            additional_info: Extra fields to include
        
        Returns:
            True if successful
        """
        if not SLACK_WEBHOOK_URL:
            logger.warning("Slack webhook URL not configured")
            return False
        
        # Color based on severity
        colors = {
            AlertLevel.INFO: "#0099ff",
            AlertLevel.WARNING: "#ffcc00",
            AlertLevel.CRITICAL: "#ff0000",
        }
        
        # Emoji based on severity
        emojis = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.CRITICAL: "🚨",
        }
        
        fields = [
            {
                "title": "Timestamp",
                "value": datetime.now(UTC).isoformat(),
                "short": True,
            }
        ]
        
        if additional_info:
            for key, value in additional_info.items():
                fields.append({
                    "title": key,
                    "value": str(value),
                    "short": True,
                })
        
        payload = {
            "channel": SLACK_CHANNEL,
            "attachments": [
                {
                    "color": colors.get(level, colors[AlertLevel.INFO]),
                    "title": f"{emojis.get(level, '📌')} {title}",
                    "text": message,
                    "fields": fields,
                    "ts": int(datetime.now(UTC).timestamp()),
                }
            ],
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(SLACK_WEBHOOK_URL, json=payload)
                if response.status_code == 200:
                    logger.info(f"Slack alert sent: {title}")
                    return True
                else:
                    logger.error(f"Slack alert failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    @staticmethod
    async def send_email_alert(
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        recipients: Optional[list[str]] = None,
    ) -> bool:
        """
        Send alert via email.
        
        Args:
            subject: Email subject
            message: Plain text message
            html_message: HTML message (optional)
            recipients: List of recipients (uses config default if not provided)
        
        Returns:
            True if successful
        """
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured")
            return False
        
        recipients = recipients or ALERT_EMAIL_RECIPIENTS
        if not recipients:
            logger.warning("No email recipients configured")
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM
            msg["To"] = ", ".join(recipients)
            
            # Attach plain text
            msg.attach(MIMEText(message, "plain"))
            
            # Attach HTML if provided
            if html_message:
                msg.attach(MIMEText(html_message, "html"))
            
            # Send email
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, recipients, msg.as_string())
            
            logger.info(f"Email alert sent: {subject}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    @staticmethod
    async def send_pagerduty_alert(
        title: str,
        description: str,
        severity: str = "warning",
        service_key: Optional[str] = None,
    ) -> bool:
        """
        Send alert to PagerDuty.
        
        Args:
            title: Alert title
            description: Alert description
            severity: error, warning, or info
            service_key: Optional override for integration key
        
        Returns:
            True if successful
        """
        key = service_key or PAGERDUTY_INTEGRATION_KEY
        if not key:
            logger.warning("PagerDuty integration key not configured")
            return False
        
        payload = {
            "routing_key": key,
            "event_action": "trigger",
            "dedup_key": f"radar-{datetime.now(UTC).timestamp()}",
            "payload": {
                "summary": title,
                "timestamp": datetime.now(UTC).isoformat(),
                "severity": severity,
                "source": "Radar API",
                "custom_details": {
                    "description": description,
                }
            },
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                )
                if response.status_code == 202:
                    logger.info(f"PagerDuty alert sent: {title}")
                    return True
                else:
                    logger.error(f"PagerDuty alert failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
            return False
    
    @staticmethod
    async def send_multi_channel_alert(
        title: str,
        message: str,
        level: str = AlertLevel.WARNING,
        use_slack: bool = True,
        use_email: bool = False,
        use_pagerduty: bool = False,
        additional_info: Optional[dict] = None,
    ) -> dict:
        """
        Send alert to multiple channels simultaneously.
        
        Args:
            title: Alert title
            message: Alert message
            level: Severity level
            use_slack: Send to Slack
            use_email: Send via email
            use_pagerduty: Send to PagerDuty
            additional_info: Extra fields for Slack
        
        Returns:
            Dictionary with results for each channel
        """
        results = {}
        
        # Send to all configured channels
        tasks = []
        
        if use_slack:
            tasks.append(("slack", AlertManager.send_slack_alert(
                message=message,
                title=title,
                level=level,
                additional_info=additional_info,
            )))
        
        if use_email:
            tasks.append(("email", AlertManager.send_email_alert(
                subject=title,
                message=message,
            )))
        
        if use_pagerduty:
            tasks.append(("pagerduty", AlertManager.send_pagerduty_alert(
                title=title,
                description=message,
                severity=level,
            )))
        
        # Execute all tasks concurrently
        if tasks:
            channel_names = [t[0] for t in tasks]
            channel_tasks = [t[1] for t in tasks]
            
            responses = await asyncio.gather(*channel_tasks, return_exceptions=True)
            
            for channel, response in zip(channel_names, responses):
                if isinstance(response, Exception):
                    results[channel] = False
                    logger.error(f"Alert to {channel} failed: {response}")
                else:
                    results[channel] = response
        
        return results


# Convenience functions
async def alert_critical(title: str, message: str, additional_info: Optional[dict] = None):
    """Send critical alert to all channels."""
    return await AlertManager.send_multi_channel_alert(
        title=title,
        message=message,
        level=AlertLevel.CRITICAL,
        use_slack=True,
        use_email=True,
        use_pagerduty=True,
        additional_info=additional_info,
    )


async def alert_warning(title: str, message: str):
    """Send warning alert to Slack."""
    return await AlertManager.send_multi_channel_alert(
        title=title,
        message=message,
        level=AlertLevel.WARNING,
        use_slack=True,
        use_email=False,
    )


async def alert_info(title: str, message: str):
    """Send info alert to Slack."""
    return await AlertManager.send_multi_channel_alert(
        title=title,
        message=message,
        level=AlertLevel.INFO,
        use_slack=True,
        use_email=False,
    )
