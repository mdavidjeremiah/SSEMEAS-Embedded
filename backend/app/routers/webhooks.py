"""WhatsApp delivery receipts (sent -> delivered -> read, or failed)."""
import hmac
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from ..config import settings
from ..db import execute

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/whatsapp")
def verify_subscription(mode: str = Query(None, alias="hub.mode"), challenge: str = Query(None, alias="hub.challenge"),
                        token: str = Query(None, alias="hub.verify_token")):
    if mode == "subscribe" and settings.wa_verify_token and hmac.compare_digest(token or "", settings.wa_verify_token):
        return PlainTextResponse(challenge)
    raise HTTPException(403, "Bad verify token")


@router.post("/whatsapp")
async def receive_status(request: Request):
    raw = await request.body()
    if settings.wa_app_secret:
        expected = "sha256=" + hmac.new(settings.wa_app_secret.encode(), raw, "sha256").hexdigest()
        if not hmac.compare_digest(expected, request.headers.get("x-hub-signature-256", "")):
            raise HTTPException(403, "Bad signature")
    for entry in json.loads(raw or "{}").get("entry", []):
        for change in entry.get("changes", []):
            for status in change.get("value", {}).get("statuses", []):
                execute("UPDATE notifications SET state=? WHERE provider_id=?", status["status"], status["id"])
    return {}
