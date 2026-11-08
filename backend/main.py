"""SSMEAS backend entry point.   Run:  uvicorn main:app --host 0.0.0.0 --port 8000
Serves the API at /api/v1 (docs at /docs) and the dashboard at /."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routers import admin, auth, dashboard, device, live, profile, webhooks
from app.seed import seed_first_run
from app.services.watcher import run_watcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_first_run()
    watcher = asyncio.create_task(run_watcher())
    yield
    watcher.cancel()


app = FastAPI(title="SSMEAS API", lifespan=lifespan)

for router in (auth.router, device.router, dashboard.router, profile.router, admin.router, webhooks.router, live.router):
    app.include_router(router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return {"ok": True}


app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")   # keep last
