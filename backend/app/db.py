"""SQLite access. A connection per call keeps this simple and thread-safe for a prototype.
To move to PostgreSQL later, replace this module; the rest of the app only uses fetch_all, fetch_one and execute."""
import sqlite3
from contextlib import contextmanager

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    email TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
    active INTEGER NOT NULL DEFAULT 1, phone TEXT NOT NULL DEFAULT '', phone_verified INTEGER NOT NULL DEFAULT 0, prefs TEXT);

CREATE TABLE IF NOT EXISTS tanks(
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, location TEXT NOT NULL DEFAULT '',
    depth_cm REAL NOT NULL, sensor_offset_cm REAL NOT NULL, warn_pct REAL NOT NULL, danger_pct REAL NOT NULL,
    hysteresis_pct REAL NOT NULL DEFAULT 3, offline_after_s INTEGER NOT NULL DEFAULT 120, device_key_hash TEXT NOT NULL,
    level_pct REAL NOT NULL DEFAULT 0, distance_cm REAL, status TEXT NOT NULL DEFAULT 'offline',
    last_seen INTEGER NOT NULL DEFAULT 0, rssi INTEGER, last_reminder INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS access(email TEXT, tank_id INTEGER, PRIMARY KEY(email, tank_id));

CREATE TABLE IF NOT EXISTS readings(tank_id INTEGER, ts INTEGER, distance_cm REAL, level_pct REAL, valid INTEGER);
CREATE INDEX IF NOT EXISTS readings_by_tank_time ON readings(tank_id, ts);

CREATE TABLE IF NOT EXISTS alerts(
    id TEXT PRIMARY KEY, tank_id INTEGER, tank_name TEXT, ts INTEGER, type TEXT, level_pct REAL,
    acknowledged INTEGER NOT NULL DEFAULT 0, acknowledged_by TEXT, acknowledged_at INTEGER);

CREATE TABLE IF NOT EXISTS notifications(
    id INTEGER PRIMARY KEY AUTOINCREMENT, alert_id TEXT, email TEXT, provider_id TEXT, state TEXT, ts INTEGER, kind TEXT);

CREATE TABLE IF NOT EXISTS phone_codes(email TEXT PRIMARY KEY, code_hash TEXT, expires REAL);
CREATE TABLE IF NOT EXISTS password_resets(token_hash TEXT PRIMARY KEY, email TEXT, expires REAL);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(settings.db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def fetch_all(sql: str, *args) -> list[dict]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, args)]


def fetch_one(sql: str, *args) -> dict | None:
    rows = fetch_all(sql, *args)
    return rows[0] if rows else None


def execute(sql: str, *args) -> int:
    with connect() as conn:
        return conn.execute(sql, args).lastrowid


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
