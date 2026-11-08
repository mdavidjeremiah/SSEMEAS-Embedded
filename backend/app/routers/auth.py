import asyncio
import secrets
import time

from fastapi import APIRouter, HTTPException

from .. import repo
from ..config import settings
from ..db import execute, fetch_one
from ..schemas import Credentials, EmailBody, ResetBody
from ..security import create_token, hash_password, limiter, sha256, verify_password
from ..services.notifier import send_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: Credentials):
    if repo.get_user(body.email):
        raise HTTPException(409, "That email is already registered")
    repo.create_user(body.email, hash_password(body.password))
    return create_token(body.email)          # new users see no tanks until an admin assigns some


@router.post("/login")
def login(body: Credentials):
    limiter.check(body.email)
    user = repo.get_user(body.email)
    if not user:
        verify_password(body.password, hash_password("x"))      # keep timing similar whether or not the email exists
    if not user or not verify_password(body.password, user["password_hash"]):
        limiter.record(body.email)
        raise HTTPException(401, "Wrong email or password")
    if not user["active"]:
        raise HTTPException(403, "This account is turned off. Ask an admin.")
    limiter.clear(body.email)
    return create_token(body.email)


@router.post("/forgot")
async def forgot_password(body: EmailBody):
    key = "forgot:" + body.email
    limiter.check(key)
    limiter.record(key)
    if repo.get_user(body.email):
        token = secrets.token_urlsafe(32)
        execute("INSERT INTO password_resets VALUES(?,?,?)", sha256(token), body.email, time.time() + 3600)
        text = f"Open this link within one hour:\n{settings.base_url}/#reset/{token}\n\nIf you did not ask for this, ignore this email."
        await asyncio.to_thread(send_email, body.email, "Reset your SSMEAS password", text)
    return {}                                  # same answer whether or not the email has an account


@router.post("/reset")
def reset_password(body: ResetBody):
    row = fetch_one("SELECT * FROM password_resets WHERE token_hash=?", sha256(body.token))
    if not row or row["expires"] < time.time():
        raise HTTPException(400, "This reset link has expired. Ask for a new one.")
    execute("UPDATE users SET password_hash=? WHERE email=?", hash_password(body.password), row["email"])
    execute("DELETE FROM password_resets WHERE email=?", row["email"])
    return {}
