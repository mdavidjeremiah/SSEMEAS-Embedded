import os
import sys
import tempfile
from pathlib import Path

# Must be set before the app is imported.
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["WATCH_SECONDS"] = "1"
os.environ["REMINDER_MINUTES"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.services import notifier


@pytest.fixture(scope="session")
def sent():
    """Captures WhatsApp and email instead of sending."""
    return {"whatsapp": [], "email": []}


@pytest.fixture(scope="session")
def client(sent):
    async def fake_whatsapp(to, template, params):
        sent["whatsapp"].append((to, template, params))
        return True, f"wamid-{len(sent['whatsapp'])}"

    notifier.send_whatsapp = fake_whatsapp
    notifier.send_email = lambda to, subject, body: sent["email"].append(body)
    import main
    with TestClient(main.app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_token(client):
    return client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["token"]


DEVICE = {"X-API-Key": "dev-device-key"}
