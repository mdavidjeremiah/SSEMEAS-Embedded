"""Endpoints the ESP32 calls. Authenticated by the per-tank device key in the X-API-Key header."""
from fastapi import APIRouter, Depends, Header, HTTPException

from .. import repo
from ..schemas import Reading
from ..security import sha256
from ..services.readings import handle_reading, now_ms

router = APIRouter(tags=["device"])
last_post: dict[int, int] = {}


def device_tank(x_api_key: str = Header(...)) -> dict:
    tank = repo.tank_by_key_hash(sha256(x_api_key))
    if not tank:
        raise HTTPException(401, "Unknown device key")
    return tank


@router.post("/readings", status_code=201)
async def post_reading(reading: Reading, tank: dict = Depends(device_tank)):
    if now_ms() - last_post.get(tank["id"], 0) < 500:
        raise HTTPException(429, "Too many readings")
    last_post[tank["id"]] = now_ms()
    return await handle_reading(tank, reading.distance_cm, now_ms(), reading.rssi)


@router.post("/readings/batch", status_code=201)
async def post_batch(readings: list[Reading], tank: dict = Depends(device_tank)):
    """Readings the device saved while it had no Wi-Fi. Up to 500 per request."""
    batch = sorted(readings[:500], key=lambda r: r.ts or 0)
    for r in batch:
        await handle_reading(tank, r.distance_cm, r.ts or now_ms(), r.rssi, live=False)
    return {"stored": len(batch)}
