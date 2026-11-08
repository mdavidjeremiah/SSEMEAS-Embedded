"""The signed-in user's profile: WhatsApp number, verification and notification preferences."""
import hmac
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..db import execute, fetch_one
from ..schemas import CodeBody, PhoneBody, Prefs
from ..security import current_user, limiter, sha256
from ..services.notifier import local_now, send_whatsapp

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("")
def get_me(user: dict = Depends(current_user)):
    return {k: user[k] for k in ("email", "role", "phone", "phone_verified", "prefs")}


@router.put("/phone")
async def set_phone(body: PhoneBody, user: dict = Depends(current_user)):
    """Save the number and send a 6-digit code on WhatsApp. The number is not used for alerts until verified."""
    key = "code:" + user["email"]
    limiter.check(key)
    limiter.record(key)
    code = f"{secrets.randbelow(10**6):06d}"
    execute("UPDATE users SET phone=?, phone_verified=0 WHERE email=?", body.number, user["email"])
    execute("REPLACE INTO phone_codes VALUES(?,?,?)", user["email"], sha256(code), time.time() + 600)
    ok, _ = await send_whatsapp(body.number, settings.wa_code_template, [code])
    if not ok:
        raise HTTPException(502, "Could not send the WhatsApp code. Check the number and try again.")
    return {"phone": body.number, "phone_verified": False}


@router.post("/phone/verify")
def verify_phone(body: CodeBody, user: dict = Depends(current_user)):
    key = "verify:" + user["email"]
    limiter.check(key)
    row = fetch_one("SELECT * FROM phone_codes WHERE email=?", user["email"])
    if not row or row["expires"] < time.time() or not hmac.compare_digest(row["code_hash"], sha256(body.code)):
        limiter.record(key)
        raise HTTPException(400, "That code is not right or has expired")
    execute("UPDATE users SET phone_verified=1 WHERE email=?", user["email"])
    execute("DELETE FROM phone_codes WHERE email=?", user["email"])
    return {"phone_verified": True}


@router.delete("/phone")
def remove_phone(user: dict = Depends(current_user)):
    execute("UPDATE users SET phone='', phone_verified=0 WHERE email=?", user["email"])
    return {}


@router.post("/phone/test")
async def send_test_message(user: dict = Depends(current_user)):
    if not user["phone_verified"]:
        raise HTTPException(400, "Verify your number first")
    params = ["Test tank", "0", "Test message", local_now().strftime("%H:%M")]
    ok, _ = await send_whatsapp(user["phone"], settings.wa_alert_template, params)
    if not ok:
        raise HTTPException(502, "WhatsApp did not accept the message")
    return {}


@router.put("/prefs")
def set_prefs(prefs: Prefs, user: dict = Depends(current_user)):
    execute("UPDATE users SET prefs=? WHERE email=?", prefs.model_dump_json(), user["email"])
    return prefs
