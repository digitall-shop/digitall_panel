from packages.common.vpnpanel_common.config import get_settings
from packages.common.vpnpanel_common.logging import configure_logging, get_logger
from packages.common.vpnpanel_common.metrics import metrics_app, service_info
from fastapi import FastAPI
import asyncio

settings = get_settings()
configure_logging(service_name="collector", level=settings.log_level)
log = get_logger("collector")

app = FastAPI(title="Collector", version="0.1.0")
app.mount("/metrics", metrics_app)
service_info.labels(service="collector", version="0.1.0").set(1)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "collector"}

# Placeholder gRPC server bootstrap (future) run in background
async def start_grpc_server():  # pragma: no cover
    while True:
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup():
    log.info("collector_startup")
    asyncio.create_task(start_grpc_server())

