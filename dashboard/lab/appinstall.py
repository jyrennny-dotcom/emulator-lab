"""Installs TikTok / YouTube on a phone without you doing it by hand:
1. from the saved copy in data/apk-cache (made from any phone that already has the app), or
2. copied straight from another running phone that has it, or
3. through the Play Store: opens the app's page and presses Install (needs a Google account
   signed in on that phone; signing in is always done by a person, never by this code)."""
import re
import shutil
import subprocess
import time

from . import adb, config, log

NO_WINDOW = 0x08000000
CACHE = config.DATA_DIR / "apk-cache"


class InstallError(RuntimeError):
    pass


def _adb(cfg, args, timeout):
    done = subprocess.run([str(config.adb_exe(cfg))] + args, capture_output=True, text=True,
                          timeout=timeout, creationflags=NO_WINDOW, encoding="utf-8", errors="replace")
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def _cached(pkg):
    folder = CACHE / pkg
    return sorted(folder.glob("*.apk")) if folder.exists() else []


def save_copy(cfg, serial, pkg):
    """Pulls the app's APK files from a phone that has it into data/apk-cache/<pkg>."""
    paths = [l.replace("package:", "").strip() for l in adb.shell(cfg, serial, f"pm path {pkg}").splitlines()
             if l.startswith("package:")]
    if not paths:
        raise InstallError(f"{pkg} is not on {serial}")
    tmp = CACHE / f"{pkg}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    for i, path in enumerate(paths):
        code, out = _adb(cfg, ["-s", serial, "pull", path, str(tmp / f"{i:02d}-{path.rsplit('/', 1)[-1]}")], 600)
        if code != 0:
            shutil.rmtree(tmp)
            raise InstallError(f"Could not copy {pkg}: {out[-200:]}")
    final = CACHE / pkg
    if final.exists():
        shutil.rmtree(final)
    tmp.rename(final)
    log.event(f"saved a copy of {pkg} from {serial} ({len(paths)} files)")


def install_copy(cfg, serial, pkg):
    files = _cached(pkg)
    code, out = _adb(cfg, ["-s", serial, "install-multiple", "-r"] + [str(f) for f in files], 900)
    if code != 0 or "Success" not in out:
        raise InstallError(f"Installing the saved copy failed: {out[-300:]}")
    log.event(f"installed {pkg} on {serial} from the saved copy")


def _screen_nodes(cfg, serial):
    adb.shell(cfg, serial, "uiautomator dump /sdcard/lab-ui.xml", timeout=30)
    xml = adb.shell(cfg, serial, "cat /sdcard/lab-ui.xml", timeout=30)
    nodes = []
    for node in re.findall(r"<node [^>]*>", xml):
        text = (re.search(r' text="([^"]*)"', node) or [None, ""])[1]
        desc = (re.search(r' content-desc="([^"]*)"', node) or [None, ""])[1]
        box = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
        if box:
            x1, y1, x2, y2 = map(int, box.groups())
            nodes.append(((text or desc).strip(), (x1 + x2) // 2, (y1 + y2) // 2))
    return nodes


def play_store(cfg, serial, pkg, wait_seconds=240):
    """Opens the Play Store page and presses Install. Returns when the app is installed."""
    adb.open_store_page(cfg, serial, pkg)
    pressed = False
    end = time.time() + wait_seconds
    while time.time() < end:
        if adb.installed(cfg, serial, [pkg]):
            log.event(f"installed {pkg} on {serial} from the Play Store")
            return
        if not pressed:
            labels = _screen_nodes(cfg, serial)
            names = {name.lower() for name, _, _ in labels}
            if "sign in" in names:
                raise InstallError("Sign in to Google in the Play Store on this phone first "
                                   "(use Phone screen), then press Open again.")
            for name, x, y in labels:
                if name.lower() == "install":
                    adb.shell(cfg, serial, f"input tap {x} {y}")
                    pressed = True
                    break
            if "your device isn't compatible with this version." in names:
                raise InstallError("The Play Store says this phone isn't compatible with the app.")
        time.sleep(4)
    raise InstallError("The Play Store install did not finish in time. Check Phone screen.")


def ensure(cfg, serial, app, phones):
    """Makes sure the app is on this phone. phones: serials of other booted phones."""
    if adb.installed(cfg, serial, app["packages"]):
        return "already installed"
    for pkg in app["packages"]:
        if _cached(pkg):
            install_copy(cfg, serial, pkg)
            return "installed from the saved copy"
    for other in phones:
        have = adb.installed(cfg, other, app["packages"])
        if have:
            save_copy(cfg, other, have[0])
            install_copy(cfg, serial, have[0])
            return f"copied from {other}"
    pkg = app["packages"][0]
    play_store(cfg, serial, pkg)
    try:
        save_copy(cfg, serial, pkg)  # so the next phones get it without the Play Store
    except InstallError as exc:
        log.error(f"could not save a copy of {pkg}: {exc}")
    return "installed from the Play Store"
