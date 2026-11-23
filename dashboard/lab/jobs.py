"""Runs slow actions (start, reboot, reset) in the background, one at a time per emulator.
Also keeps a short activity feed that the dashboard and the friend view show."""
import collections
import threading
import time

from . import log

_jobs = {}
_lock = threading.Lock()
feed = collections.deque(maxlen=60)


def note(text):
    feed.appendleft({"time": time.strftime("%H:%M:%S"), "text": text})


def current(emu_id):
    with _lock:
        return dict(_jobs.get(emu_id) or {})


def busy(emu_id):
    return current(emu_id).get("running", False)


def run(emu_id, label, action, fn):
    """Starts fn() in a thread. Refuses if this emulator is already doing something."""
    with _lock:
        if (_jobs.get(emu_id) or {}).get("running"):
            raise RuntimeError(f"{label} is busy: {_jobs[emu_id]['message']}")
        _jobs[emu_id] = {"running": True, "action": action, "message": f"{action}...", "ok": None}
    note(f"{label}: {action.lower()}…")

    def work():
        try:
            result = fn()
            message = f"{action} done" + (f" ({result})" if isinstance(result, str) else "")
            ok = True
        except Exception as exc:  # shown to the user, so keep it readable
            message, ok = f"{action} failed: {exc}", False
            log.error(f"{label}: {message}")
        with _lock:
            _jobs[emu_id] = {"running": False, "action": action, "message": message, "ok": ok}
        note(f"{label}: {message}")

    threading.Thread(target=work, daemon=True).start()
