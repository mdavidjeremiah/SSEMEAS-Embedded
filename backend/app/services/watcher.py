"""Background loop: offline detection, reminders while a tank stays in Warning/Danger, and data retention."""
import asyncio
import time

from .. import repo
from ..config import settings
from ..db import execute, fetch_all
from ..tasks import spawn
from . import notifier
from .readings import now_ms, raise_event
from .realtime import hub


async def check_tanks() -> None:
    now = now_ms()
    for tank in fetch_all("SELECT * FROM tanks"):
        if tank["status"] != "offline" and now - tank["last_seen"] > tank["offline_after_s"] * 1000:
            execute("UPDATE tanks SET status='offline' WHERE id=?", tank["id"])
            tank["status"] = "offline"
            await raise_event(tank, "offline")
            await hub.send_to_viewers(tank["id"], {"type": "tank", "tank": repo.tank_public(tank)})
        elif tank["status"] in ("warning", "danger"):
            remind_if_due(tank, now)


def remind_if_due(tank: dict, now: int) -> None:
    alert = repo.last_alert(tank["id"], ("warning", "danger"))
    if not alert or alert["acknowledged"]:       # reminders stop once someone acknowledges, or the tank recovers
        return
    if now - max(tank["last_reminder"], alert["ts"]) >= settings.reminder_minutes * 60_000:
        execute("UPDATE tanks SET last_reminder=? WHERE id=?", now, tank["id"])
        spawn(notifier.notify_subscribers(tank, tank["status"], alert["id"], reminder=True))


def clean_old_data(now: int) -> None:
    execute("DELETE FROM readings WHERE ts<?", now - settings.retention_days * 86_400_000)
    execute("DELETE FROM phone_codes WHERE expires<?", time.time())
    execute("DELETE FROM password_resets WHERE expires<?", time.time())


async def run_watcher() -> None:
    last_cleanup = 0
    while True:
        await asyncio.sleep(settings.watch_seconds)
        await check_tanks()
        if now_ms() - last_cleanup > 86_400_000:
            last_cleanup = now_ms()
            clean_old_data(last_cleanup)
