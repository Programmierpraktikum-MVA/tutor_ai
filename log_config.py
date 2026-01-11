import logging
import os


def setup_logging() -> None:
    """Configure a concise logging format for the bot."""
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
