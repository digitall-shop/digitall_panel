from fastapi import FastAPI
from packages.common.vpnpanel_common.config import Settings
from packages.common.vpnpanel_common.logging import configure_logging
from packages.common.vpnpanel_common.metrics import metrics_app

settings = Settings()
configure_logging(service_name="control-api")

app = FastAPI(title="Control API", version="0.1.0")
app.mount("/metrics", metrics_app)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "control-api"}

# TODO: integrate existing legacy app code under /app into this service gradually.

