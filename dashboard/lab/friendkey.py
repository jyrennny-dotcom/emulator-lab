"""The secret key inside the friend link. Making a new key stops the old link working."""
import hmac
import secrets

from . import config

FILE = config.DATA_DIR / "friend-key.txt"


def get():
    if not FILE.exists():
        return new()
    return FILE.read_text(encoding="utf-8").strip()


def new():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(24)
    FILE.write_text(key, encoding="utf-8")
    return key


def matches(candidate):
    return bool(candidate) and hmac.compare_digest(str(candidate), get())
