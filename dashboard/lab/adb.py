"""Talks to emulators through adb: device list, boot state, installed apps, launching apps."""
import subprocess

from . import config

NO_WINDOW = 0x08000000  # keeps a console window from flashing up on Windows


class AdbError(RuntimeError):
    pass


def run(cfg, args, serial=None, timeout=15):
    exe = config.adb_exe(cfg)
    if not exe.exists():
        raise AdbError("adb is not installed yet. Run scripts\\setup.ps1.")
    cmd = [str(exe)] + (["-s", serial] if serial else []) + list(args)
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              creationflags=NO_WINDOW, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        raise AdbError(f"adb timed out after {timeout}s: {' '.join(args)}")
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def ensure_server(cfg):
    run(cfg, ["start-server"], timeout=30)


def devices(cfg):
    """Returns {serial: state}. State is 'device', 'offline', 'unauthorized' and so on."""
    code, out = run(cfg, ["devices"], timeout=20)
    found = {}
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("*"):
            found[parts[0]] = parts[1]
    return found


def reconnect_offline(cfg):
    run(cfg, ["reconnect", "offline"], timeout=20)
    return devices(cfg)


def shell(cfg, serial, command, timeout=15):
    code, out = run(cfg, ["shell", command], serial=serial, timeout=timeout)
    return out.strip()


def getprop(cfg, serial, prop):
    return shell(cfg, serial, f"getprop {prop}")


def booted(cfg, serial):
    return getprop(cfg, serial, "sys.boot_completed") == "1"


def installed(cfg, serial, packages):
    """Returns the subset of packages that are installed on the device."""
    out = shell(cfg, serial, "pm list packages", timeout=20)
    have = {line.replace("package:", "").strip() for line in out.splitlines()}
    return [p for p in packages if p in have]


def launch(cfg, serial, package):
    out = shell(cfg, serial, f"monkey -p {package} -c android.intent.category.LAUNCHER 1")
    if "No activities found" in out or "Error" in out:
        raise AdbError(f"Could not open {package}: {out[-200:]}")


def open_store_page(cfg, serial, package):
    """Opens the Play Store page so you can install the app yourself."""
    shell(cfg, serial, f"am start -a android.intent.action.VIEW -d market://details?id={package}")


def reboot(cfg, serial):
    run(cfg, ["reboot"], serial=serial, timeout=30)


def emu_kill(cfg, serial):
    """Asks the emulator to shut down cleanly (saves its quick-boot state)."""
    run(cfg, ["emu", "kill"], serial=serial, timeout=30)


def avd_name(cfg, serial):
    code, out = run(cfg, ["emu", "avd", "name"], serial=serial, timeout=10)
    return out.splitlines()[0].strip() if out else ""
