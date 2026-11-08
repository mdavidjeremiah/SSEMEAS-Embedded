"""Read endpoints for the dashboard: tanks, history, stats, CSV export, alerts."""
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from .. import repo
from ..db import execute, fetch_all, fetch_one
from ..security import current_user
from ..services.readings import now_ms

router = APIRouter(tags=["dashboard"])


def get_tank_or_404(user: dict, tank_id: int) -> dict:
    tank = repo.visible_tank(user, tank_id)
    if not tank:
        raise HTTPException(404, "Tank not found")
    return tank


@router.get("/tanks")
def list_tanks(user: dict = Depends(current_user)):
    return [repo.tank_public(t) for t in repo.visible_tanks(user)]


@router.get("/tanks/{tank_id}/readings")
def history(tank_id: int, minutes: int = Query(360, ge=1, le=43200), user: dict = Depends(current_user)):
    """Level over time, averaged into about 600 buckets so long ranges stay fast."""
    get_tank_or_404(user, tank_id)
    bucket = max(1, minutes * 60_000 // 600)
    return fetch_all(
        "SELECT (ts/?)*? AS ts, AVG(level_pct) AS level FROM readings "
        "WHERE tank_id=? AND valid=1 AND ts>=? GROUP BY 1 ORDER BY 1", bucket, bucket, tank_id, now_ms() - minutes * 60_000)


@router.get("/tanks/{tank_id}/stats")
def stats(tank_id: int, minutes: int = Query(360, ge=1, le=43200), user: dict = Depends(current_user)):
    get_tank_or_404(user, tank_id)
    since = now_ms() - minutes * 60_000
    summary = fetch_one("SELECT MAX(level_pct) AS peak, AVG(level_pct) AS avg FROM readings WHERE tank_id=? AND valid=1 AND ts>=?", tank_id, since)
    danger_events = fetch_one("SELECT COUNT(*) AS n FROM alerts WHERE tank_id=? AND type='danger' AND ts>=?", tank_id, since)["n"]
    return {"peak": summary["peak"], "avg": summary["avg"], "danger_events": danger_events, "eta_minutes": minutes_to_full(tank_id)}


def minutes_to_full(tank_id: int) -> int | None:
    """Estimate from the fill rate over the last 30 minutes (None when the tank is not filling)."""
    points = fetch_all("SELECT ts, level_pct FROM readings WHERE tank_id=? AND valid=1 AND ts>=? ORDER BY ts", tank_id, now_ms() - 30 * 60_000)
    if len(points) < 6:
        return None
    start = sum(p["level_pct"] for p in points[:3]) / 3          # averaging 3 points at each end smooths noise
    end = sum(p["level_pct"] for p in points[-3:]) / 3
    minutes = (points[-1]["ts"] - points[0]["ts"]) / 60_000 or 1
    rate = (end - start) / minutes                                # percent per minute
    return round((100 - end) / rate) if rate > 0.02 else None


@router.get("/tanks/{tank_id}/export.csv")
def export_csv(tank_id: int, minutes: int = Query(1440, ge=1, le=43200), user: dict = Depends(current_user)):
    tank = get_tank_or_404(user, tank_id)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["time_utc", "distance_cm", "level_pct", "valid"])
    for r in fetch_all("SELECT * FROM readings WHERE tank_id=? AND ts>=? ORDER BY ts", tank_id, now_ms() - minutes * 60_000):
        when = datetime.fromtimestamp(r["ts"] / 1000, timezone.utc).isoformat(timespec="seconds")
        writer.writerow([when, r["distance_cm"], round(r["level_pct"], 1), r["valid"]])
    filename = tank["name"].replace(" ", "_")
    return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'})


@router.get("/alerts")
def list_alerts(user: dict = Depends(current_user)):
    ids = [t["id"] for t in repo.visible_tanks(user)]
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    alerts = fetch_all(f"SELECT id, tank_id, tank_name, ts, type, level_pct, acknowledged FROM alerts "
                       f"WHERE tank_id IN ({marks}) ORDER BY ts DESC LIMIT 200", *ids)
    for alert in alerts:
        states = fetch_all("SELECT state, COUNT(*) AS n FROM notifications WHERE alert_id=? GROUP BY state", alert["id"])
        alert["acknowledged"] = bool(alert["acknowledged"])
        alert["delivery"] = ", ".join(f'{s["n"]} {s["state"]}' for s in states) or "Not sent"
    return alerts


@router.post("/alerts/{alert_id}/ack")
def acknowledge(alert_id: str, user: dict = Depends(current_user)):
    alert = fetch_one("SELECT * FROM alerts WHERE id=?", alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    get_tank_or_404(user, alert["tank_id"])
    execute("UPDATE alerts SET acknowledged=1, acknowledged_by=?, acknowledged_at=? WHERE id=?", user["email"], now_ms(), alert_id)
    return {}
