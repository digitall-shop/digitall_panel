import logging
import structlog
from typing import Optional


def configure_logging(service_name: str, level: str = "INFO") -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    structlog.configure(
        processors=[
            timestamper,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.get_logger().bind(service=service_name)


def get_logger(name: Optional[str] = None):  # type: ignore
    return structlog.get_logger(name)

