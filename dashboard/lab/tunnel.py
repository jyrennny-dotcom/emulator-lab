"""Keeps the friend link open: runs a Cloudflare quick tunnel to the friend side (port 8766 only)
and restarts it if it drops. The current link is saved to data/friend-link.txt."""
import ctypes
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from . import config, friendkey, jobs, log

NO_WINDOW = 0x08000000
DETACHED = NO_WINDOW | 0x00000200  # no window, and keeps running when the dashboard restarts
LINK_FILE = config.DATA_DIR / "friend-link.txt"
_state = {"url": "", "status": "off", "pid": None}
METRICS_PORT = 8767  # cloudflared's local status page; /quicktunnel there gives the link's address


def find_cloudflared():
    found = shutil.which("cloudflared")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        path = Path(base) / "cloudflared" / "cloudflared.exe"
        if path.exists():
            return str(path)
    link = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "cloudflared.exe"
    return str(link) if link.exists() else None


def link():
    """The full friend link with its key, or '' while the tunnel is not ready."""
    return f"{_state['url']}/?key={friendkey.get()}" if _state["url"] else ""


def status():
    return {"status": _state["status"], "link": link()}


def _running_tunnels(port):
    """PIDs of cloudflared already tunnelling to our port (left over from an earlier dashboard run)."""
    query = ("Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe'\" | "
             f"Where-Object {{ $_.CommandLine -like '*127.0.0.1:{port}*' }} | ForEach-Object {{ $_.ProcessId }}")
    done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", query],
                          capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW)
    return [int(x) for x in done.stdout.split() if x.isdigit()]


def _alive(pid):
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel32.CloseHandle(handle)
    return code.value == 259  # STILL_ACTIVE


def _ask_tunnel():
    """Asks the running tunnel itself for its address (its local /quicktunnel page).
    More reliable than reading the log, which another run may have overwritten."""
    for metrics_port in (METRICS_PORT, 20241, 20242, 20243, 20244, 20245):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{metrics_port}/quicktunnel", timeout=2) as res:
                host = json.loads(res.read()).get("hostname", "")
            if host.endswith(".trycloudflare.com"):
                return f"https://{host}"
        except (OSError, ValueError):
            continue
    return ""


def _run_once(exe, port):
    """Reuses a tunnel that is still running (so the link stays the same), else starts a new one.
    The tunnel runs detached, so restarting the dashboard does not change the friend link."""
    log_path = config.LOG_DIR / "tunnel.log"
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    existing = _running_tunnels(port)
    for extra in existing[1:]:  # only one tunnel should ever run
        subprocess.run(["taskkill", "/PID", str(extra), "/F"], capture_output=True, creationflags=NO_WINDOW)
    if existing and _ask_tunnel():
        pid = existing[0]
        log.event(f"reusing friend link (cloudflared pid {pid})")
    else:
        if existing:
            subprocess.run(["taskkill", "/PID", str(existing[0]), "/F"], capture_output=True, creationflags=NO_WINDOW)
        cmd = [exe, "tunnel", "--no-autoupdate", "--metrics", f"127.0.0.1:{METRICS_PORT}",
               "--url", f"http://127.0.0.1:{port}"]
        with open(log_path, "w", encoding="utf-8", errors="replace") as out:
            pid = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, creationflags=DETACHED).pid
    _state.update(pid=pid, status="starting", url="")
    deadline = time.time() + 60
    while _alive(pid):
        if not _state["url"]:
            url = _ask_tunnel()
            if url:
                _state.update(url=url, status="on")
                config.DATA_DIR.mkdir(parents=True, exist_ok=True)
                LINK_FILE.write_text(link(), encoding="utf-8")
                log.event("friend link open")
                jobs.note("Friend link is live")
            elif time.time() > deadline:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, creationflags=NO_WINDOW)
                break
        time.sleep(2)
    _state.update(url="", status="restarting")


def _keep_alive(exe, port):
    wait = 5
    while True:
        try:
            _run_once(exe, port)
        except OSError as exc:
            log.error(f"tunnel: {exc}")
        if LINK_FILE.exists():
            LINK_FILE.unlink()
        log.event(f"friend link dropped, retrying in {wait}s")
        time.sleep(wait)
        wait = min(wait * 2, 120)


def start(cfg):
    exe = find_cloudflared()
    if not exe:
        _state["status"] = "cloudflared not installed (run scripts\\share-link.ps1 once)"
        return False
    threading.Thread(target=_keep_alive, args=(exe, cfg["friendPort"]), daemon=True).start()
    return True
