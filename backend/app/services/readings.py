"""What happens when a reading arrives: store it, classify it, raise alerts, push it to dashboards."""
import secrets
import time

from .. import repo
from ..constants import EVENT_LABELS, SENSOR_MAX_CM, SENSOR_MIN_CM
from ..db import execute
from ..tasks import spawn
from . import notifier, status
from .realtime import hub

now_ms = lambda: int(time.time() * 1000)


async def raise_event(tank: dict, kind: str) -> None:
    alert_id = secrets.token_hex(6)
    execute("INSERT INTO alerts(id,tank_id,tank_name,ts,type,level_pct) VALUES(?,?,?,?,?,?)",
            alert_id, tank["id"], tank["name"], now_ms(), kind, tank["level_pct"])
    severity = {"recovery": "safe", "offline": "danger"}.get(kind, kind)
    text = f'{tank["name"]}: {EVENT_LABELS[kind].lower()} ({tank["level_pct"]:.0f}%)'
    await hub.send_to_viewers(tank["id"], {"type": "alert", "message": text, "severity": severity})
    spawn(notifier.notify_subscribers(tank, kind, alert_id))     # never make the device wait for WhatsApp


async def handle_reading(tank: dict, distance_cm: float, ts: int, rssi: int | None = None, live: bool = True) -> dict:
    """live=False is for readings the ESP32 buffered during an outage: they fill the history but trigger no alerts."""
    valid = SENSOR_MIN_CM <= distance_cm <= SENSOR_MAX_CM
    level = status.level_pct(distance_cm, tank["depth_cm"], tank["sensor_offset_cm"])
    execute("INSERT INTO readings VALUES(?,?,?,?,?)", tank["id"], ts, distance_cm, level, int(valid))
    if not (live and valid):
        return {"level_pct": round(level, 1), "status": tank["status"], "valid": valid}

    previous = tank["status"]
    new_status = status.classify(level, previous, tank["warn_pct"], tank["danger_pct"], tank["hysteresis_pct"])
    execute("UPDATE tanks SET level_pct=?, distance_cm=?, status=?, last_seen=?, rssi=? WHERE id=?",
            level, round(distance_cm), new_status, ts, rssi, tank["id"])
    tank = {**tank, "level_pct": level, "distance_cm": round(distance_cm), "status": new_status, "last_seen": ts, "rssi": rssi}

    if new_status != previous:
        kind = event_for_change(tank, previous, new_status)
        if kind:
            execute("UPDATE tanks SET last_reminder=? WHERE id=?", ts, tank["id"])
            await raise_event(tank, kind)
    await hub.send_to_viewers(tank["id"], {"type": "tank", "tank": repo.tank_public(tank), "point": {"ts": ts, "level": level}})
    return {"level_pct": round(level, 1), "status": new_status, "valid": True}


def event_for_change(tank: dict, previous: str, new_status: str) -> str | None:
    if new_status != "safe":
        return new_status
    if previous != "offline":
        return "recovery"
    # Coming back from offline straight into Safe: only announce it if we had announced the outage.
    last = repo.last_alert(tank["id"])
    return "recovery" if last and last["type"] == "offline" else None
