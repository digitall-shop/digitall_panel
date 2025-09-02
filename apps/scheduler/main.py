from fastapi import FastAPI
from packages.common.vpnpanel_common.config import get_settings
from packages.common.vpnpanel_common.logging import configure_logging, get_logger
from packages.common.vpnpanel_common.metrics import metrics_app, service_info
import asyncio

settings = get_settings()
configure_logging(service_name="scheduler", level=settings.log_level)
log = get_logger("scheduler")

app = FastAPI(title="Scheduler", version="0.1.0")
app.mount("/metrics", metrics_app)
service_info.labels(service="scheduler", version="0.1.0").set(1)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "scheduler"}

async def periodic_tasks():  # pragma: no cover
    interval = settings.scheduler_interval_seconds
    while True:
        log.info("scheduler_tick", interval=interval)
        # TODO: quota enforcement, rollups, partition maintenance
        await asyncio.sleep(interval)

@app.on_event("startup")
async def startup():
    log.info("scheduler_startup")
    asyncio.create_task(periodic_tasks())

