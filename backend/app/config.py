"""Settings, read from environment variables (and an optional .env file in backend/)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_dotenv()
env = os.getenv


class Settings:
    # Core
    jwt_secret = env("JWT_SECRET", "dev-change-me")
    db_path = env("DB_PATH", str(ROOT / "ssmeas.db"))
    base_url = env("BASE_URL", "http://localhost:8000")
    timezone = env("TZ_NAME", "Africa/Kampala")          # used for quiet hours and message times
    frontend_dir = Path(env("FRONTEND_DIR", str(ROOT.parent / "frontend")))

    # First-run seed (change these!)
    admin_email = env("ADMIN_EMAIL", "admin@example.com")
    admin_password = env("ADMIN_PASSWORD", "admin123")
    demo_device_key = env("DEMO_DEVICE_KEY", "dev-device-key")

    # WhatsApp Cloud API. If token or phone id is missing, messages are printed instead of sent.
    wa_token = env("WA_TOKEN")
    wa_phone_id = env("WA_PHONE_ID")
    wa_alert_template = env("WA_ALERT_TEMPLATE", "tank_alert")
    wa_code_template = env("WA_CODE_TEMPLATE", "verify_code")
    wa_verify_token = env("WA_VERIFY_TOKEN")
    wa_app_secret = env("WA_APP_SECRET")

    # Email for password resets. If SMTP_HOST is missing, the email is printed instead.
    smtp_host = env("SMTP_HOST")
    smtp_port = int(env("SMTP_PORT", "587"))
    smtp_user = env("SMTP_USER")
    smtp_password = env("SMTP_PASS")
    smtp_from = env("SMTP_FROM", "alerts@ssmeas.local")

    # Behaviour
    reminder_minutes = int(env("REMINDER_MINUTES", "30"))
    retention_days = int(env("RETENTION_DAYS", "90"))
    watch_seconds = int(env("WATCH_SECONDS", "30"))


settings = Settings()
if settings.jwt_secret == "dev-change-me":
    print("WARNING: JWT_SECRET is not set. Set it before deploying.")
