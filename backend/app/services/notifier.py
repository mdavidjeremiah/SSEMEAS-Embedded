"""Outgoing messages: WhatsApp (Meta Cloud API) and email."""
import asyncio
import secrets
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import httpx

from .. import repo
from ..config import settings
from ..constants import EVENT_LABELS
from ..db import execute

GRAPH_URL = "https://graph.facebook.com/v20.0"   # check Meta's docs for the current API version


def local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


async def send_whatsapp(to: str, template: str, params: list[str]) -> tuple[bool, str | None]:
    """Send a template message. Returns (ok, provider message id). Retries with backoff on network errors and 5xx/429."""
    if not (settings.wa_token and settings.wa_phone_id):
        print(f"[WhatsApp dry-run] to={to} template={template} params={params}")
        return True, "dry-" + secrets.token_hex(4)
    body = {
        "messaging_product": "whatsapp", "to": to.lstrip("+"), "type": "template",
        "template": {"name": template, "language": {"code": "en"},
                     "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]},
    }
    headers = {"Authorization": f"Bearer {settings.wa_token}"}
    for wait in (0, 1, 3):
        await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{GRAPH_URL}/{settings.wa_phone_id}/messages", json=body, headers=headers)
            if response.is_success:
                return True, response.json()["messages"][0]["id"]
            if response.status_code < 500 and response.status_code != 429:
                break               # a client error will not fix itself on retry
        except httpx.HTTPError:
            pass
    return False, None


def is_quiet_hour(hour: int, start: int, end: int) -> bool:
    if start == end:
        return False
    return start <= hour < end if start < end else (hour >= start or hour < end)


async def notify_subscribers(tank: dict, kind: str, alert_id: str, reminder: bool = False) -> None:
    """Send an alert to each verified user who wants this kind of event. Warning can be muted overnight; Danger never is."""
    now = local_now()
    for user in repo.subscribers(tank["id"]):
        prefs = user["prefs"]
        if not prefs.get(kind):
            continue
        if kind == "warning" and prefs["quiet_on"] and is_quiet_hour(now.hour, prefs["quiet_from"], prefs["quiet_to"]):
            continue
        status_text = EVENT_LABELS[kind] + (" (reminder)" if reminder else "")
        params = [tank["name"], f'{tank["level_pct"]:.0f}', status_text, now.strftime("%H:%M")]
        ok, provider_id = await send_whatsapp(user["phone"], settings.wa_alert_template, params)
        execute("INSERT INTO notifications(alert_id,email,provider_id,state,ts,kind) VALUES(?,?,?,?,?,?)",
                alert_id, user["email"], provider_id, "sent" if ok else "failed",
                int(time.time() * 1000), "reminder" if reminder else "alert")


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        print(f"[email dry-run] to={to}\n{subject}\n{body}")
        return
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.smtp_from, to, subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
