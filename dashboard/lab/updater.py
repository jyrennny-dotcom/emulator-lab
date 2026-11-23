"""Keeps this copy up to date: every few minutes it asks GitHub for the newest version and,
if there is one, downloads it and swaps the code in. data/ and logs/ are never touched, and your
own hardware choices (RAM, cores, resolution, DPI, which phones start) are kept.
The dashboard then restarts itself (server.py watches its code) and open pages reload."""
import io
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from . import config, jobs, log

VERSION_FILE = config.DATA_DIR / "version.txt"
KEEP_DIRS = {"data", "logs", ".git"}
LOCAL_FIELDS = ("ramMB", "cores", "width", "height", "dpi", "enabled")
UA = {"User-Agent": "emulator-lab-updater"}


def _get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as res:
        return res.read()


def latest(repo, branch="main"):
    data = json.loads(_get(f"https://api.github.com/repos/{repo}/commits/{branch}"))
    return data["sha"]


def current():
    return VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""


def _merge_config(new_text, old_path):
    """New config from the update, but keep this PC's own hardware choices."""
    new = json.loads(new_text)
    if old_path.exists():
        old = json.loads(old_path.read_text(encoding="utf-8-sig"))
        mine = {e["id"]: e for e in old.get("emulators", [])}
        for emu in new.get("emulators", []):
            for key in LOCAL_FIELDS:
                if emu["id"] in mine and key in mine[emu["id"]]:
                    emu[key] = mine[emu["id"]][key]
    return json.dumps(new, indent=2) + "\n"


def apply(repo, sha):
    blob = _get(f"https://codeload.github.com/{repo}/zip/{sha}", timeout=120)
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(io.BytesIO(blob)).extractall(tmp)
        top = next(Path(tmp).iterdir())  # GitHub puts everything in one folder
        for src in top.rglob("*"):
            rel = src.relative_to(top)
            if src.is_dir() or rel.parts[0] in KEEP_DIRS:
                continue
            dst = config.ROOT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if rel.as_posix() == "config/lab.json":
                dst.write_text(_merge_config(src.read_text(encoding="utf-8-sig"), dst), encoding="utf-8")
            elif not dst.exists() or dst.read_bytes() != src.read_bytes():
                shutil.copyfile(src, dst)  # server.py waits 2 s after a change, so it restarts on the full set
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(sha, encoding="utf-8")


def check(cfg):
    """Returns a short message. Never raises: a failed check just waits for the next one."""
    repo = cfg.get("updateRepo", "")
    if not repo:
        return "updates off"
    if (config.ROOT / ".git").exists():
        return "this is the source copy (git), it is never overwritten by updates"
    try:
        sha = latest(repo, cfg.get("updateBranch", "main"))
        if sha == current():
            return "up to date"
        apply(repo, sha)
        log.event(f"updated to {sha[:7]}")
        jobs.note(f"Updated to the newest version ({sha[:7]})")
        return f"updated to {sha[:7]}"
    except Exception as exc:  # offline, GitHub busy, etc.
        log.error(f"update check failed: {exc}")
        return f"update check failed: {exc}"
