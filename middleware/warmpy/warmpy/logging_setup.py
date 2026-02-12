import logging
from pathlib import Path

from .paths import WARMPY_DIR, LOG_FILE


def setup_logging() -> Path:
    """Configure logging to ~/.warmpy/warmpy.log."""
    WARMPY_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    logging.info("=== WarmPy started ===")
    return LOG_FILE
