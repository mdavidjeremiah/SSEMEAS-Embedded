"""Queries the rest of the app needs. Keeping SQL here keeps routers and services readable."""
import json

from .constants import DEFAULT_PREFS
from .db import execute, fetch_all, fetch_one


# ---------- users ----------
def get_user(email: str) -> dict | None:
    user = fetch_one("SELECT * FROM users WHERE email=?", email)
    if not user:
        return None
    user["active"] = bool(user["active"])
    user["phone_verified"] = bool(user["phone_verified"])
    user["prefs"] = {**DEFAULT_PREFS, **json.loads(user["prefs"] or "{}")}
    user["tanks"] = [r["tank_id"] for r in fetch_all("SELECT tank_id FROM access WHERE email=?", email)]
    return user


def create_user(email: str, password_hash: str, role: str = "user") -> None:
    execute("INSERT INTO users(email, password_hash, role, prefs) VALUES(?,?,?,?)",
            email, password_hash, role, json.dumps(DEFAULT_PREFS))


def all_users() -> list[dict]:
    return [get_user(r["email"]) for r in fetch_all("SELECT email FROM users ORDER BY email")]


def set_user_tanks(email: str, tank_ids: list[int]) -> None:
    execute("DELETE FROM access WHERE email=?", email)
    for tank_id in tank_ids:
        execute("INSERT OR IGNORE INTO access VALUES(?,?)", email, tank_id)


def subscribers(tank_id: int) -> list[dict]:
    """Active users with a verified WhatsApp number who can see this tank."""
    emails = fetch_all(
        "SELECT email FROM users WHERE active=1 AND phone_verified=1 AND phone!='' "
        "AND (role='admin' OR email IN (SELECT email FROM access WHERE tank_id=?))", tank_id)
    return [get_user(r["email"]) for r in emails]


# ---------- tanks ----------
def visible_tanks(user: dict) -> list[dict]:
    if user["role"] == "admin":
        return fetch_all("SELECT * FROM tanks ORDER BY id")
    return fetch_all("SELECT * FROM tanks WHERE id IN (SELECT tank_id FROM access WHERE email=?) ORDER BY id", user["email"])


def visible_tank(user: dict, tank_id: int) -> dict | None:
    return next((t for t in visible_tanks(user) if t["id"] == tank_id), None)


def can_view_tank(email: str, tank_id: int) -> bool:
    return fetch_one(
        "SELECT 1 AS ok FROM users u WHERE email=? AND (role='admin' OR EXISTS("
        "SELECT 1 FROM access a WHERE a.email=u.email AND a.tank_id=?))", email, tank_id) is not None


def tank_by_key_hash(key_hash: str) -> dict | None:
    return fetch_one("SELECT * FROM tanks WHERE device_key_hash=?", key_hash)


def tank_public(t: dict) -> dict:
    keys = ("id", "name", "location", "depth_cm", "warn_pct", "danger_pct", "level_pct", "distance_cm", "status", "last_seen", "rssi")
    return {k: t[k] for k in keys}


def tank_admin(t: dict) -> dict:
    keys = ("id", "name", "location", "depth_cm", "sensor_offset_cm", "warn_pct", "danger_pct", "hysteresis_pct", "offline_after_s", "status")
    return {k: t[k] for k in keys}


# ---------- alerts ----------
def last_alert(tank_id: int, types: tuple[str, ...] | None = None) -> dict | None:
    if types:
        marks = ",".join("?" * len(types))
        return fetch_one(f"SELECT * FROM alerts WHERE tank_id=? AND type IN ({marks}) ORDER BY ts DESC LIMIT 1", tank_id, *types)
    return fetch_one("SELECT * FROM alerts WHERE tank_id=? ORDER BY ts DESC LIMIT 1", tank_id)
