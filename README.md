# SSMEAS: Smart Sewage Level Monitoring

ESP32 + HC-SR04 reads the sewage level and alerts locally. A FastAPI backend stores the readings, applies the alert rules and sends WhatsApp messages. A plain HTML/CSS/JS dashboard shows it live.

```
ssmeas/
├── backend/                FastAPI + SQLite
│   ├── main.py             entry point (serves the API and the dashboard)
│   ├── app/
│   │   ├── config.py       settings from environment variables / .env
│   │   ├── db.py, repo.py  database and queries
│   │   ├── security.py     passwords, login tokens, rate limiting
│   │   ├── schemas.py      request validation
│   │   ├── routers/        auth, device (ESP32), dashboard, profile, admin, webhooks, live (WebSocket)
│   │   └── services/       status (level + hysteresis), readings, notifier (WhatsApp, email), realtime, watcher
│   ├── tests/              pytest suite
│   └── simulate.py         pretends to be the ESP32
├── frontend/               no framework, no build step (ES modules)
│   ├── index.html, css/styles.css
│   └── js/                 main, auth, service, remote (real API), mock (demo), store, ui, views/
└── firmware/ssmeas_esp32/  Arduino sketch: config.h (edit this), sensor.h, alerts.h, network.h
```

## Run it

```
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. First run creates `ssmeas.db`, an admin (`admin@example.com` / `admin123`) and a demo tank whose device key is `dev-device-key`. Change all three before deploying (see `.env.example`).

`--host 0.0.0.0` matters: without it the ESP32 cannot reach the backend, only your own computer can.

- **Try the dashboard without a backend:** serve the `frontend` folder (for example `python -m http.server` inside it) and open `/?mock=1`. It runs simulated tanks in the browser. The page uses ES modules, so it must be served over http, not opened as a file.
- **Try the backend without hardware:** `python backend/simulate.py` posts fake readings every 2 seconds.
- **Run the tests:** `pip install -r requirements-dev.txt && pytest` inside `backend/`.

## Connect the ESP32

1. Dashboard, Admin, Add a tank. Copy the **device key** (shown once).
2. Open `firmware/ssmeas_esp32/config.h` and set the Wi-Fi name and password, `SERVER_URL` (your computer's LAN IP, for example `http://192.168.1.50:8000`), `DEVICE_KEY`, and the tank depth, offset and thresholds (same as in Admin).
3. Arduino IDE: board **ESP32 Dev Module**, upload, open the Serial Monitor at 115200 baud. You should see `POST /api/v1/readings -> 201`.

Wiring: HC-SR04 TRIG to GPIO 5, ECHO to GPIO 18 **through a 1k/2k divider**, LEDs on 25/26/27, buzzer transistor on 14. Pins are constants in `config.h`.

## Configuration (environment variables or `backend/.env`)

| Variable | Purpose |
| --- | --- |
| `JWT_SECRET` | Signing key for login tokens. Required in production |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `DEMO_DEVICE_KEY` | First-run seed values |
| `WA_TOKEN`, `WA_PHONE_ID` | WhatsApp Cloud API. Unset means a dry run (messages print to the console) |
| `WA_ALERT_TEMPLATE` (`tank_alert`), `WA_CODE_TEMPLATE` (`verify_code`) | Approved template names. `tank_alert` has 4 body variables: tank, level %, status, time. `verify_code` has 1: the code |
| `WA_VERIFY_TOKEN`, `WA_APP_SECRET` | Webhook `/api/v1/webhooks/whatsapp` for delivery receipts |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` | Password-reset email. Unset means the link prints to the console |
| `BASE_URL` | Public URL used in reset links |
| `REMINDER_MINUTES` (30), `RETENTION_DAYS` (90), `TZ_NAME` (Africa/Kampala) | Reminder interval, how long raw readings are kept, timezone for quiet hours |

## API summary (`/api/v1`, interactive docs at `/docs`)

| Who | Endpoints |
| --- | --- |
| ESP32 (header `X-API-Key`) | `POST /readings`, `POST /readings/batch` |
| Signed-in users | `GET /tanks`, `/tanks/{id}/readings`, `/tanks/{id}/stats`, `/tanks/{id}/export.csv`, `/alerts`, `POST /alerts/{id}/ack`, `/me*`, WebSocket `/ws` |
| Admins | `/admin/users`, `/admin/tanks`, `/admin/notifications` |
| Public | `POST /auth/register`, `/auth/login`, `/auth/forgot`, `/auth/reset`, `GET /health` |

## Before going live

- Set `JWT_SECRET`, change the admin password, and replace the demo device key.
- Use HTTPS. Set `USE_TLS 1` in the firmware and load your server's root certificate instead of `setInsecure()`.
- SQLite on free hosting may be wiped on redeploy. Use a persistent disk or move `db.py` to PostgreSQL.
- Register the two WhatsApp templates and confirm current Meta pricing and API version.
- Check the sensor against a tape measure at two or three levels and correct the depth and offset.
