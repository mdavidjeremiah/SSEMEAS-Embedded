"""Passwords, login tokens, request guards and a small in-memory rate limiter."""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException

from . import repo
from .config import settings


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt = stored.split("$")[0]
    return hmac.compare_digest(hash_password(password, salt), stored)


def create_token(email: str) -> dict:
    expires = datetime.now(timezone.utc) + timedelta(hours=12)
    return {"token": jwt.encode({"sub": email, "exp": expires}, settings.jwt_secret, "HS256")}


def user_from_token(token: str) -> dict:
    try:
        email = jwt.decode(token, settings.jwt_secret, ["HS256"])["sub"]
    except Exception:
        raise HTTPException(401, "Not signed in")
    user = repo.get_user(email)
    if not user or not user["active"]:
        raise HTTPException(401, "Not signed in")
    return user


def current_user(authorization: str = Header("")) -> dict:
    return user_from_token(authorization.removeprefix("Bearer "))


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Admins only")
    return user


class RateLimiter:
    """Allows `limit` recorded failures per key in `window` seconds."""

    def __init__(self, limit: int = 5, window: int = 300):
        self.limit, self.window, self.events = limit, window, {}

    def check(self, key: str) -> None:
        recent = [t for t in self.events.get(key, []) if time.time() - t < self.window]
        self.events[key] = recent
        if len(recent) >= self.limit:
            raise HTTPException(429, "Too many attempts. Wait a few minutes and try again.")

    def record(self, key: str) -> None:
        self.events.setdefault(key, []).append(time.time())

    def clear(self, key: str) -> None:
        self.events.pop(key, None)


limiter = RateLimiter()
