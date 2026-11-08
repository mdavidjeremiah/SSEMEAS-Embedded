import time

from app.services.status import classify, level_pct
from conftest import DEVICE, auth


# ---------- pure logic ----------
def test_level_calculation():
    assert level_pct(180, 180, 20) == 0            # empty
    assert level_pct(20, 180, 20) == 100           # at the full line
    assert round(level_pct(100, 180, 20), 1) == 50
    assert level_pct(5, 180, 20) == 100            # clamped


def test_classify_with_hysteresis():
    c = lambda lvl, prev: classify(lvl, prev, 70, 85, 3)
    assert c(50, "safe") == "safe"
    assert c(72, "safe") == "warning"
    assert c(90, "warning") == "danger"
    assert c(83, "danger") == "danger"             # still inside the hysteresis band
    assert c(81, "danger") == "warning"
    assert c(68, "warning") == "warning"           # band under Warning
    assert c(66, "warning") == "safe"


# ---------- auth ----------
def test_login_and_roles(client, admin_token):
    assert client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong-pass"}).status_code == 401
    token = client.post("/api/v1/auth/register", json={"email": "u@x.com", "password": "secret1"}).json()["token"]
    assert client.get("/api/v1/tanks", headers=auth(token)).json() == []          # nothing assigned yet
    assert client.get("/api/v1/admin/users", headers=auth(token)).status_code == 403
    assert client.get("/api/v1/tanks").status_code == 401


def test_password_reset(client, sent):
    client.post("/api/v1/auth/register", json={"email": "r@x.com", "password": "secret1"})
    client.post("/api/v1/auth/forgot", json={"email": "r@x.com"})
    token = sent["email"][-1].split("#reset/")[1].split()[0]
    assert client.post("/api/v1/auth/reset", json={"token": token, "password": "newpass1"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "r@x.com", "password": "newpass1"}).status_code == 200
    assert client.post("/api/v1/auth/reset", json={"token": token, "password": "again12"}).status_code == 400   # single use


# ---------- the whole device -> alert -> WhatsApp -> dashboard path ----------
def test_device_flow(client, admin_token, sent):
    assert client.post("/api/v1/readings", json={"distance_cm": 60}, headers={"X-API-Key": "bad"}).status_code == 401

    user = client.post("/api/v1/auth/login", json={"email": "u@x.com", "password": "secret1"}).json()["token"]
    client.patch("/api/v1/admin/users/u@x.com", json={"tanks": [1]}, headers=auth(admin_token))
    assert len(client.get("/api/v1/tanks", headers=auth(user)).json()) == 1

    # WhatsApp number: set -> wrong code rejected -> right code accepted
    client.put("/api/v1/me/phone", json={"number": "+256772123456"}, headers=auth(user))
    code = sent["whatsapp"][-1][2][0]
    assert client.post("/api/v1/me/phone/verify", json={"code": "000000"}, headers=auth(user)).status_code == 400
    assert client.post("/api/v1/me/phone/verify", json={"code": code}, headers=auth(user)).json()["phone_verified"] is True
    client.put("/api/v1/me/prefs", json={"warning": True, "danger": True, "recovery": True, "offline": True}, headers=auth(user))
    sent["whatsapp"].clear()

    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text(user)
        results = []
        for distance in (150, 60, 30, 60, 100):                # safe, warning, danger, back to warning, safe
            results.append(client.post("/api/v1/readings", json={"distance_cm": distance, "rssi": -60}, headers=DEVICE).json()["status"])
            time.sleep(0.6)                                    # the endpoint rejects readings faster than every 0.5 s
        assert results == ["safe", "warning", "danger", "warning", "safe"]
        kinds = [ws.receive_json()["type"] for _ in range(3)]
        assert kinds == ["tank", "alert", "tank"]              # reading, then the warning alert, then the next reading

    time.sleep(1.5)
    alerts = client.get("/api/v1/alerts", headers=auth(user)).json()
    types = [a["type"] for a in alerts if a["type"] != "offline"]
    assert types[:4] == ["recovery", "warning", "danger", "warning"] or {"recovery", "warning", "danger"} <= set(types)
    assert all("sent" in a["delivery"] for a in alerts if a["type"] in ("warning", "danger"))
    assert any(m[2][2].startswith("Danger") for m in sent["whatsapp"])

    stats = client.get("/api/v1/tanks/1/stats", headers=auth(user)).json()
    assert stats["danger_events"] == 1 and stats["peak"] > 90
    assert client.get("/api/v1/tanks/1/readings", headers=auth(user)).json()
    assert len(client.get("/api/v1/tanks/1/export.csv", headers=auth(user)).text.splitlines()) >= 6
    assert client.post(f"/api/v1/alerts/{alerts[0]['id']}/ack", headers=auth(user)).status_code == 200


def test_invalid_and_batch_readings(client):
    time.sleep(0.6)
    bad = client.post("/api/v1/readings", json={"distance_cm": 900}, headers=DEVICE).json()
    assert bad["valid"] is False
    batch = [{"distance_cm": 100, "ts": int(time.time() * 1000) - 60000}]
    assert client.post("/api/v1/readings/batch", json=batch, headers=DEVICE).json() == {"stored": 1}


# ---------- admin ----------
def test_admin_tanks_and_users(client, admin_token):
    h = auth(admin_token)
    body = {"name": "T2", "location": "x", "depth_cm": 150, "sensor_offset_cm": 15, "warn_pct": 70, "danger_pct": 85}
    created = client.post("/api/v1/admin/tanks", json=body, headers=h)
    assert created.status_code == 201 and created.json()["device_key"]
    bad = client.post("/api/v1/admin/tanks", json={**body, "warn_pct": 90}, headers=h)
    assert bad.status_code == 422
    assert client.post("/api/v1/admin/tanks/2/rotate-key", headers=h).json()["device_key"]
    assert client.get("/api/v1/admin/notifications", headers=h).status_code == 200
    assert client.patch("/api/v1/admin/users/admin@example.com", json={"active": False}, headers=h).status_code == 400   # no self-lockout
    client.patch("/api/v1/admin/users/r@x.com", json={"active": False}, headers=h)
    assert client.post("/api/v1/auth/login", json={"email": "r@x.com", "password": "newpass1"}).status_code == 403


def test_offline_detection_and_recovery(client, admin_token):
    from app.db import execute
    user = client.post("/api/v1/auth/login", json={"email": "u@x.com", "password": "secret1"}).json()["token"]
    execute("UPDATE tanks SET last_seen=1 WHERE id=1")
    time.sleep(2.2)                                            # the watcher runs every second in tests
    assert client.get("/api/v1/tanks", headers=auth(user)).json()[0]["status"] == "offline"
    time.sleep(0.6)
    client.post("/api/v1/readings", json={"distance_cm": 150}, headers=DEVICE)
    assert client.get("/api/v1/alerts", headers=auth(user)).json()[0]["type"] == "recovery"


def test_dashboard_is_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/health").json() == {"ok": True}
