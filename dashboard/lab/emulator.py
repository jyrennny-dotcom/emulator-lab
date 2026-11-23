"""Creates, starts, stops, reboots and resets one emulator. Brings its window to the front."""
import ctypes
import os
import re
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

from . import adb, config, log, procstats

NO_WINDOW = 0x08000000
# no console window at all (DETACHED made Windows open a Terminal window for the emulator);
# the emulator still keeps running if the dashboard closes
DETACHED = NO_WINDOW | 0x00000200


class LabError(RuntimeError):
    pass


def reset_phrase(emu):
    return f"RESET {emu['name']}"


def is_running(emu):
    info = procstats.snapshot(max_age=0).get(emu["avd"])
    return bool(info and info["pids"])


def _env_with_java():
    """avdmanager needs JAVA_HOME. If it is missing or wrong, find Java 17+ in the usual places."""
    env = dict(os.environ)
    if (Path(env.get("JAVA_HOME", "")) / "bin" / "java.exe").exists():
        return env
    roots = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / name
             for name in ("Eclipse Adoptium", "Microsoft", "Java", r"Android\Android Studio")]
    for root in roots:
        for java in sorted(root.glob("*/bin/java.exe"), reverse=True) if root.exists() else []:
            if re.search(r"jdk-(1[7-9]|2\d)|jbr", str(java)):
                env["JAVA_HOME"] = str(java.parents[1])
                return env
    return env


def create_avd(cfg, emu):
    """Makes the emulator if it does not exist yet. Never overwrites one that does."""
    if config.avd_dir(emu).exists():
        return False
    tool = config.avdmanager_bat(cfg)
    if not tool.exists():
        raise LabError("avdmanager is missing. Run scripts\\setup.ps1 first.")
    # A .bat runs through cmd, which splits words at ';' unless they are quoted, so build the line by hand
    cmd = (f'"{tool}" create avd -n {emu["avd"]} -k "{cfg["systemImage"]}" -d {emu["device"]}')
    done = subprocess.run(cmd, input="no\n", capture_output=True, text=True, timeout=180,
                          creationflags=NO_WINDOW, env=_env_with_java())
    if done.returncode != 0 or not config.avd_dir(emu).exists():
        raise LabError(f"Could not create {emu['name']}: {(done.stdout + done.stderr)[-400:]}")
    apply_hardware(emu, first_time=True)
    log.event(f"created {emu['name']} ({emu['avd']})")
    return True


def apply_hardware(emu, first_time=False):
    """Writes RAM, cores, resolution and DPI into the emulator's config.ini."""
    ini = config.avd_dir(emu) / "config.ini"
    if not ini.exists():
        raise LabError(f"{emu['name']} has not been created yet.")
    wanted = {
        "hw.ramSize": f"{emu['ramMB']}",
        "hw.cpu.ncore": f"{emu['cores']}",
        "hw.lcd.width": f"{emu['width']}",
        "hw.lcd.height": f"{emu['height']}",
        "hw.lcd.density": f"{emu['dpi']}",
        "hw.keyboard": "yes",
        "hw.gpu.enabled": "yes",
        "hw.gpu.mode": "auto",
        "fastboot.forceColdBoot": "no",
        "PlayStore.enabled": "yes",
    }
    if first_time:
        wanted["disk.dataPartition.size"] = "8G"
    lines, seen = [], set()
    for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
        key, _, value = (part.strip() for part in line.partition("="))
        if value in ("<temp>", "<build>"):
            continue  # placeholders from newer avdmanager; "<temp>" data would not survive a restart
        if key in wanted:
            lines.append(f"{key}={wanted[key]}")
            seen.add(key)
        else:
            lines.append(line)
    lines += [f"{k}={v}" for k, v in wanted.items() if k not in seen]
    ini.write_text("\n".join(lines) + "\n", encoding="utf-8")


def start(cfg, emu, wipe=False):
    if is_running(emu):
        raise LabError(f"{emu['name']} is already running.")
    exe = config.emulator_exe(cfg)
    if not exe.exists():
        raise LabError("The Android Emulator is not installed. Run scripts\\setup.ps1.")
    if not config.avd_dir(emu).exists():
        raise LabError(f"{emu['name']} has not been created. Run scripts\\setup.ps1.")
    apply_hardware(emu)
    args = [str(exe), "-avd", emu["avd"], "-port", str(emu["port"]), "-memory", str(emu["ramMB"]),
            "-cores", str(emu["cores"]), "-no-boot-anim", "-gpu", "auto"]
    if wipe:
        args.append("-wipe-data")
    if not cfg.get("showWindows", True):
        args.append("-no-window")  # runs hidden; use Phone screen on the dashboard instead
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.LOG_DIR / f"emulator-{emu['id']}.log"
    out = open(out_path, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(args, stdout=out, stderr=subprocess.STDOUT, creationflags=DETACHED)
    log.event(f"start {emu['name']} port {emu['port']}{' WIPE' if wipe else ''} pid {proc.pid}")
    time.sleep(6)
    if proc.poll() is not None:
        out.close()
        tail = out_path.read_text(encoding="utf-8", errors="replace")[-600:]
        log.error(f"{emu['name']} exited at startup: {tail}")
        raise LabError(f"{emu['name']} closed right after starting. Last output: {tail}")
    return proc.pid


def wait_boot(cfg, emu, timeout=None):
    """Waits until adb sees the device and Android has finished booting."""
    timeout = timeout or cfg.get("bootTimeoutSeconds", 240)
    serial = config.serial(emu)
    end = time.time() + timeout
    while time.time() < end:
        if not is_running(emu):
            raise LabError(f"{emu['name']} stopped while booting. See logs\\emulator-{emu['id']}.log")
        try:
            if adb.devices(cfg).get(serial) == "device" and adb.booted(cfg, serial):
                log.event(f"booted {emu['name']}")
                return True
        except adb.AdbError:
            pass
        time.sleep(3)
    raise LabError(f"{emu['name']} did not finish booting within {timeout}s.")


def stop(cfg, emu, force=False):
    serial = config.serial(emu)
    if not is_running(emu):
        return "already stopped"
    if force:
        for pid in procstats.snapshot(max_age=0)[emu["avd"]]["pids"]:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                           creationflags=NO_WINDOW)
        log.event(f"force stop {emu['name']}")
        return "force stopped"
    try:
        adb.emu_kill(cfg, serial)
    except adb.AdbError as exc:
        log.error(f"stop {emu['name']}: {exc}")
    end = time.time() + 45
    while time.time() < end:
        if not is_running(emu):
            log.event(f"stopped {emu['name']}")
            return "stopped"
        time.sleep(2)
    raise LabError(f"{emu['name']} is still shutting down. Wait, or use Force stop.")


def reboot(cfg, emu):
    if not is_running(emu):
        raise LabError(f"{emu['name']} is not running.")
    adb.reboot(cfg, config.serial(emu))
    log.event(f"reboot {emu['name']}")
    time.sleep(8)
    return wait_boot(cfg, emu)


def reset(cfg, emu, typed):
    """Wipes app data and accounts for ONE emulator. Needs the exact reset phrase."""
    if typed != reset_phrase(emu):
        raise LabError(f"Not reset. Type exactly: {reset_phrase(emu)}")
    log.event(f"RESET requested for {emu['name']} (confirmed)")
    if is_running(emu):
        stop(cfg, emu)
    start(cfg, emu, wipe=True)
    return wait_boot(cfg, emu)


def show_window(emu):
    user32 = ctypes.windll.user32
    found = []
    tags = (f"{emu['avd']}:{emu['port']}", f"Android Emulator - {emu['avd']}")

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if any(t in buf.value for t in tags):
                found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    if not found:
        raise LabError(f"No window found for {emu['name']}. Is it running?")
    hwnd = found[0]
    user32.ShowWindow(hwnd, 9)  # restore if minimised
    user32.keybd_event(0x12, 0, 0, 0)  # tap Alt so Windows lets us take focus
    user32.keybd_event(0x12, 0, 2, 0)
    user32.SetForegroundWindow(hwnd)
    return True
