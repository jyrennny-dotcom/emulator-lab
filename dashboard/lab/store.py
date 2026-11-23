"""Saves the checklist you fill in by hand (nicknames, app checks, notes) to data/status.json."""
import json
import os
import re
import shutil
import threading
from datetime import date

from . import config

FILE = config.DATA_DIR / "status.json"
APP_CHECKS = ["installed", "loggedIn", "rewardsVisible", "inviteUiVisible", "inviteLinkShown"]
TEST_STATES = ["not started", "in progress", "passed", "failed", "blocked"]
TEXT_LIMITS = {"nickname": 40, "accountLabel": 40, "notes": 4000, "lastChecked": 10}
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", re.I)
_SECRET_WORDS = re.compile(r"\b(password|passwd|pwd|token|otp|2fa code|cookie)\s*[:=]", re.I)
_lock = threading.Lock()


def blank(cfg):
    return {
        "nickname": "",
        "accountLabel": "",
        "testingStatus": "not started",
        "lastChecked": "",
        "notes": "",
        "apps": {a["key"]: {c: False for c in APP_CHECKS} for a in cfg["apps"]},
    }


def load_all(cfg):
    with _lock:
        saved = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    result = {}
    for emu in cfg["emulators"]:
        entry = blank(cfg)
        old = saved.get(emu["id"], {})
        for key in ("nickname", "accountLabel", "testingStatus", "lastChecked", "notes"):
            if key in old:
                entry[key] = old[key]
        for app_key, checks in old.get("apps", {}).items():
            if app_key in entry["apps"]:
                entry["apps"][app_key].update({c: bool(v) for c, v in checks.items() if c in APP_CHECKS})
        result[emu["id"]] = entry
    return result


def _clean(cfg, incoming):
    entry = blank(cfg)
    for key, limit in TEXT_LIMITS.items():
        value = str(incoming.get(key, "")).strip()
        if len(value) > limit:
            raise ValueError(f"{key} is too long (max {limit} characters)")
        entry[key] = value
    for key in ("nickname", "accountLabel"):
        if _EMAIL.search(entry[key]):
            raise ValueError("Use a nickname, not an email address, for labels.")
    if _SECRET_WORDS.search(entry["notes"]):
        raise ValueError("Notes look like they contain a password or code. Keep secrets out of files.")
    if entry["lastChecked"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["lastChecked"]):
        raise ValueError("lastChecked must be a date like 2026-11-23")
    status = incoming.get("testingStatus", "not started")
    if status not in TEST_STATES:
        raise ValueError(f"testingStatus must be one of: {', '.join(TEST_STATES)}")
    entry["testingStatus"] = status
    for app_key, checks in (incoming.get("apps") or {}).items():
        if app_key in entry["apps"]:
            entry["apps"][app_key] = {c: bool(checks.get(c, False)) for c in APP_CHECKS}
    return entry


def save_one(cfg, emu_id, incoming):
    config.find(cfg, emu_id)
    entry = _clean(cfg, incoming)
    if not entry["lastChecked"]:
        entry["lastChecked"] = date.today().isoformat()
    with _lock:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        saved = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
        if FILE.exists():
            shutil.copyfile(FILE, FILE.with_suffix(".json.bak"))
        saved[emu_id] = entry
        tmp = FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(saved, indent=2), encoding="utf-8")
        os.replace(tmp, FILE)
    return entry
