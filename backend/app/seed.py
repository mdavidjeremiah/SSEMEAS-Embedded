"""First run only: create a demo admin and a demo tank so the system works straight away."""
from . import repo
from .config import settings
from .db import execute, fetch_one
from .security import hash_password, sha256


def seed_first_run() -> None:
    if fetch_one("SELECT 1 AS x FROM users"):
        return
    repo.create_user(settings.admin_email, hash_password(settings.admin_password), "admin")
    execute("INSERT INTO tanks(name,location,depth_cm,sensor_offset_cm,warn_pct,danger_pct,hysteresis_pct,offline_after_s,device_key_hash) "
            "VALUES('Home septic tank','Muyenga, Kampala',180,20,70,85,3,120,?)", sha256(settings.demo_device_key))
