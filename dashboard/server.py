"""Dashboard web server.
Port 8765: your dashboard, this PC only (127.0.0.1).
Port 8766: the friend side, same dashboard but only with the secret key from the friend link.
Both listen on 127.0.0.1 only; the friend side reaches the internet only through scripts\\share-link.ps1."""
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lab import (actions, adb, config, emulator, friendkey, jobs, log, screen, state, store,  # noqa: E402
                 tunnel, updater)

STATIC = Path(__file__).resolve().parent / "static"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}
_fails = {"count": 0, "since": time.time()}


class Handler(BaseHTTPRequestHandler):
    remote = False
    port = 0
    server_version = "EmulatorLab"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    # ---------- replies ----------
    def _send(self, code, body, ctype="application/json", extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code, message):
        self._send(code, {"ok": False, "error": message})

    # ---------- who may use it ----------
    def _allowed(self, query):
        if not self.remote:
            host = (self.headers.get("Host") or "").lower()
            return host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}")
        cookie = SimpleCookie(self.headers.get("Cookie") or "")
        given = (query.get("key") or [""])[0] or (cookie["lab_key"].value if "lab_key" in cookie else "")
        if friendkey.matches(given):
            return True
        if time.time() - _fails["since"] > 60:
            _fails.update(count=0, since=time.time())
        _fails["count"] += 1
        if _fails["count"] > 20:
            time.sleep(2)  # slows down anyone guessing keys
        return False

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 100_000:
            raise ValueError("Request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    # ---------- GET ----------
    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if not self._allowed(query):
            return self._send(403, b"<h1>This link is not valid.</h1><p>Ask for a new friend link.</p>",
                              "text/html; charset=utf-8")
        extra = {}
        if self.remote and "key" in query:
            extra["Set-Cookie"] = f"lab_key={friendkey.get()}; HttpOnly; SameSite=Strict; Path=/"
        path = url.path
        if path in ("/", "/index.html"):
            page = (STATIC / "index.html").read_bytes()
            page = page.replace(b"__MODE__", b"friend" if self.remote else b"owner")
            return self._send(200, page, TYPES[".html"], extra)
        if path.startswith("/static/"):
            file = (STATIC / path[len("/static/"):]).resolve()
            if STATIC not in file.parents or not file.is_file():
                return self._error(404, "Not found")
            return self._send(200, file.read_bytes(), TYPES.get(file.suffix, "application/octet-stream"))
        cfg = config.load()
        if path == "/api/state":
            data = state.build(cfg)
            data["mode"] = "friend" if self.remote else "owner"
            # the page reloads itself when this changes, so design changes reach everyone without a refresh
            data["pageVersion"] = int(max(f.stat().st_mtime for f in STATIC.iterdir()))
            data["resetPhrases"] = {e["id"]: emulator.reset_phrase(e) for e in cfg["emulators"]}
            if not self.remote:
                data["friend"] = tunnel.status()
            return self._send(200, data)
        match = re.fullmatch(r"/api/emulators/(\d\d)/screen", path)
        if match:
            try:
                png = screen.screenshot(cfg, config.find(cfg, match.group(1)))
                return self._send(200, png, "image/png")
            except (adb.AdbError, KeyError) as exc:
                return self._error(409, str(exc))
        return self._error(404, "Not found")

    # ---------- POST ----------
    def do_POST(self):
        url = urlparse(self.path)
        if not self._allowed(parse_qs(url.query)):
            return self._error(403, "Not allowed")
        if self.headers.get("X-Lab-Request") != "1":
            return self._error(403, "Missing request header")
        try:
            body = self._body()
            result = self._route(url.path, body)
            return self._send(200, {"ok": True, "result": result})
        except (emulator.LabError, adb.AdbError, ValueError, KeyError, RuntimeError) as exc:
            return self._error(400, str(exc).strip("'\""))
        except Exception as exc:  # never crash the server; show a readable message
            log.error(f"server error on {url.path}: {exc!r}")
            return self._error(500, f"Something went wrong: {exc}")

    def _route(self, path, body):
        cfg = config.load()
        who = "Friend" if self.remote else "You"
        if path == "/api/start-all":
            jobs.note(f"{who}: start all")
            return actions.start_all(cfg)
        if path == "/api/stop-all":
            jobs.note(f"{who}: stop all")
            return actions.stop_all(cfg)
        if path == "/api/go":
            return actions.go_all(cfg, body.get("app", "tiktok"))
        if path == "/api/adb/reconnect":
            return adb.reconnect_offline(cfg)
        match = re.fullmatch(r"/api/emulators/(\d\d)/([a-z]+)", path)
        if not match:
            raise KeyError("Unknown action")
        emu, action = config.find(cfg, match.group(1)), match.group(2)
        if action == "start":
            return actions.start_one(cfg, emu)
        if action in ("stop", "forcestop"):
            return actions.stop_one(cfg, emu, force=action == "forcestop")
        if action == "reboot":
            return actions.reboot_one(cfg, emu)
        if action == "reset":
            return actions.reset_one(cfg, emu, body.get("confirm", ""))
        if action == "open":
            return actions.open_app(cfg, emu, body.get("app", "tiktok"))
        if action == "window":
            if self.remote:
                raise ValueError("The window is on the owner's PC. Use the phone screen instead.")
            return emulator.show_window(emu)
        if action == "tracking":
            return store.save_one(cfg, emu["id"], body)
        if action == "hardware":
            if emulator.is_running(emu):
                raise ValueError("Stop the emulator before changing its hardware.")
            return config.save_hardware(emu["id"], body)
        if action == "input":
            return screen.send(cfg, emu, body)
        raise KeyError("Unknown action")


class ExclusiveServer(ThreadingHTTPServer):
    """On Windows a normal server lets a second copy share the port. This makes a second copy fail and exit."""
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def serve(port, remote):
    handler = type("RemoteHandler" if remote else "LocalHandler", (Handler,), {"remote": remote, "port": port})
    httpd = ExclusiveServer(("127.0.0.1", port), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


HERE = Path(__file__).resolve().parent


def _code_stamp():
    return max(f.stat().st_mtime for f in list(HERE.glob("*.py")) + list(HERE.glob("lab/*.py")))


def _restart_if_code_changed(stamp):
    """Live updates: when the dashboard's code changes, start a fresh copy and quit this one.
    The friend link keeps running, and pages reconnect by themselves."""
    if _code_stamp() == stamp:
        return
    time.sleep(2)  # let a multi-file edit finish
    for file in list(HERE.glob("*.py")) + list(HERE.glob("lab/*.py")):
        try:
            compile(file.read_text(encoding="utf-8"), str(file), "exec")
        except SyntaxError as exc:
            log.error(f"not restarting, {file.name} has an error: {exc}")
            return
    log.event("code changed, restarting dashboard")
    subprocess.Popen([sys.executable, str(HERE / "server.py"), "--after-restart"], cwd=str(HERE),
                     creationflags=0x08000000 | 0x00000200)
    os._exit(0)


def main():
    cfg = config.load()
    tries = 15 if "--after-restart" in sys.argv else 1
    for attempt in range(tries):
        try:
            serve(cfg["dashboardPort"], remote=False)
            serve(cfg["friendPort"], remote=True)
            break
        except OSError as exc:
            if attempt == tries - 1:
                print(f"Could not open the dashboard ports ({exc}). Is it already running?")
                sys.exit(1)
            time.sleep(1)
    log.event("dashboard started")
    if cfg.get("autoShare", True):
        tunnel.start(cfg)
    print(f"Dashboard: http://127.0.0.1:{cfg['dashboardPort']}  (friend side on {cfg['friendPort']})")
    stamp = _code_stamp()
    next_update = time.time() + 20
    try:
        while True:
            time.sleep(3)
            if time.time() > next_update:  # newest version from GitHub, every 5 minutes
                next_update = time.time() + 300
                threading.Thread(target=updater.check, args=(config.load(),), daemon=True).start()
            _restart_if_code_changed(stamp)
    except KeyboardInterrupt:
        log.event("dashboard stopped (friend link keeps running)")


if __name__ == "__main__":
    main()
