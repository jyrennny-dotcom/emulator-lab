"""One shared log file: logs/lab.log (start, stop, reboot, reset and errors)."""
import logging
from logging.handlers import RotatingFileHandler

from . import config

_logger = None


def get():
    global _logger
    if _logger is None:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        _logger = logging.getLogger("lab")
        _logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(config.LOG_DIR / "lab.log", maxBytes=2_000_000,
                                      backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        _logger.addHandler(handler)
    return _logger


def event(message):
    get().info(message)


def error(message):
    get().error(message)
