import logging

from backend.core.config import settings


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("road_beyond_the_pines")


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or "road_beyond_the_pines")
