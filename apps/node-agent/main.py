import asyncio
from packages.common.vpnpanel_common.config import get_settings
from packages.common.vpnpanel_common.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(service_name="node-agent", level=settings.log_level)
log = get_logger("node-agent")

async def heartbeat_loop():  # pragma: no cover
    while True:
        log.info("node_agent_heartbeat")
        await asyncio.sleep(settings.sample_interval_seconds)

async def main():  # pragma: no cover
    log.info("node_agent_start")
    await heartbeat_loop()

if __name__ == "__main__":  # pragma: no cover
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("node_agent_stop")

