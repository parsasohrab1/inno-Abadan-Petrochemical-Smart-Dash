"""کانال‌های اعلان — ایمیل (SMTP)، پیامک (وب‌سرویس)، درون‌برنامه‌ای (Kafka→WebSocket).

در نبود پیکربندی SMTP/SMS، پیام فقط لاگ می‌شود (حالت توسعه). رابط برای اتصال به
درگاه واقعی پیامک ایران (کاوه‌نگار/قاصدک) آماده است.
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import httpx

from services.common.logging import get_logger

log = get_logger("alerting.notifier")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ALERT_EMAIL_TO = [e for e in os.getenv("ALERT_EMAIL_TO", "").split(",") if e]

SMS_API_URL = os.getenv("SMS_API_URL")
SMS_API_KEY = os.getenv("SMS_API_KEY")
ALERT_SMS_TO = [p for p in os.getenv("ALERT_SMS_TO", "").split(",") if p]

_SEVERITY_CHANNELS = {
    "info": set(),
    "warning": {"inapp"},
    "major": {"inapp", "email"},
    "critical": {"inapp", "email", "sms"},
}


def channels_for(severity: str) -> set[str]:
    return _SEVERITY_CHANNELS.get(severity, {"inapp"})


def send_email(subject: str, body: str) -> bool:
    if not (SMTP_HOST and ALERT_EMAIL_TO):
        log.info("notifier.email.skipped", subject=subject)
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER or "cbm@abadan.local"
    msg["To"] = ", ".join(ALERT_EMAIL_TO)
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD or "")
            server.send_message(msg)
        log.info("notifier.email.sent", subject=subject, to=len(ALERT_EMAIL_TO))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("notifier.email.failed", error=str(exc))
        return False


def send_sms(text: str) -> bool:
    if not (SMS_API_URL and SMS_API_KEY and ALERT_SMS_TO):
        log.info("notifier.sms.skipped")
        return False
    try:
        with httpx.Client(timeout=10) as client:
            for phone in ALERT_SMS_TO:
                client.post(SMS_API_URL, json={"apikey": SMS_API_KEY, "to": phone, "message": text})
        log.info("notifier.sms.sent", to=len(ALERT_SMS_TO))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("notifier.sms.failed", error=str(exc))
        return False


def dispatch(severity: str, title: str, description: str) -> dict:
    used = channels_for(severity)
    body = f"{title}\n\n{description}\n\n— داشبرد هوشمند CBM پتروشیمی آبادان"
    return {
        "email": send_email(title, body) if "email" in used else None,
        "sms": send_sms(f"{title} — {description}") if "sms" in used else None,
        "inapp": "inapp" in used,
    }
