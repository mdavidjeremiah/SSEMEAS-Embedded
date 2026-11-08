import secrets

from fastapi import APIRouter, Depends, HTTPException

from .. import repo
from ..db import execute, fetch_all
from ..schemas import TankIn, UserPatch
from ..security import require_admin, sha256

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users")
def list_users():
    keys = ("email", "role", "active", "tanks", "phone", "phone_verified")
    return [{k: u[k] for k in keys} for u in repo.all_users()]


@router.patch("/users/{email}")
def update_user(email: str, patch: UserPatch, admin: dict = Depends(require_admin)):
    if not repo.get_user(email):
        raise HTTPException(404, "User not found")
    if email == admin["email"] and (patch.active is False or patch.role == "user"):
        raise HTTPException(400, "You cannot lock yourself out")
    if patch.role:
        execute("UPDATE users SET role=? WHERE email=?", patch.role, email)
    if patch.active is not None:
        execute("UPDATE users SET active=? WHERE email=?", int(patch.active), email)
    if patch.tanks is not None:
        repo.set_user_tanks(email, patch.tanks)
    return {}


@router.get("/tanks")
def list_tanks():
    return [repo.tank_admin(t) for t in fetch_all("SELECT * FROM tanks ORDER BY id")]


@router.post("/tanks", status_code=201)
def create_tank(tank: TankIn):
    key = secrets.token_urlsafe(24)               # shown once; only its hash is stored
    execute("INSERT INTO tanks(name,location,depth_cm,sensor_offset_cm,warn_pct,danger_pct,hysteresis_pct,offline_after_s,device_key_hash) "
            "VALUES(?,?,?,?,?,?,?,?,?)", tank.name, tank.location, tank.depth_cm, tank.sensor_offset_cm, tank.warn_pct,
            tank.danger_pct, tank.hysteresis_pct, tank.offline_after_s, sha256(key))
    return {"device_key": key}


@router.put("/tanks/{tank_id}")
def update_tank(tank_id: int, tank: TankIn):
    execute("UPDATE tanks SET name=?,location=?,depth_cm=?,sensor_offset_cm=?,warn_pct=?,danger_pct=?,hysteresis_pct=?,offline_after_s=? WHERE id=?",
            tank.name, tank.location, tank.depth_cm, tank.sensor_offset_cm, tank.warn_pct, tank.danger_pct,
            tank.hysteresis_pct, tank.offline_after_s, tank_id)
    return {}


@router.post("/tanks/{tank_id}/rotate-key")
def rotate_key(tank_id: int):
    key = secrets.token_urlsafe(24)
    execute("UPDATE tanks SET device_key_hash=? WHERE id=?", sha256(key), tank_id)
    return {"device_key": key}


@router.delete("/tanks/{tank_id}")
def delete_tank(tank_id: int):
    for table, column in (("tanks", "id"), ("access", "tank_id"), ("readings", "tank_id"), ("alerts", "tank_id")):
        execute(f"DELETE FROM {table} WHERE {column}=?", tank_id)
    return {}


@router.get("/notifications")
def list_notifications():
    return fetch_all(
        "SELECT n.ts, n.email, n.kind, n.state, a.type, a.tank_name FROM notifications n "
        "LEFT JOIN alerts a ON a.id=n.alert_id ORDER BY n.id DESC LIMIT 100")
