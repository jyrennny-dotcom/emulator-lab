"""'What's new' list shown live on the dashboard, so your friend knows what changed and what to test.
Add one with:  python dashboard\\cli.py update "Added the phone screen"."""
import json
import os
import time

from . import config

FILE = config.DATA_DIR / "updates.json"


def load(limit=30):
    if not FILE.exists():
        return []
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))[:limit]
    except ValueError:
        return []


def add(text):
    text = " ".join(str(text).split())[:300]
    if not text:
        raise ValueError("Update text is empty")
    items = load(limit=200)
    items.insert(0, {"date": time.strftime("%Y-%m-%d %H:%M"), "text": text})
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items[:200], indent=2), encoding="utf-8")
    os.replace(tmp, FILE)
    return items[0]
