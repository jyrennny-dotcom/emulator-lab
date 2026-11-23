"""High-level actions shared by the dashboard, the HUD and the command-line scripts."""
import time

from . import adb, appinstall, config, emulator, hidewin, jobs, state


def start_one(cfg, emu, delay=0):
    def work():
        if delay:
            time.sleep(delay)
        adb.ensure_server(cfg)
        emulator.start(cfg, emu)
        if not cfg.get("showWindows", True):
            hidewin.hide_all()  # safety net: nothing shows on screen when phones run hidden
        emulator.wait_boot(cfg, emu)
        state.forget(config.serial(emu))
        return "booted"
    jobs.run(emu["id"], emu["name"], "Start", work)


def start_all(cfg):
    """Starts every enabled emulator that is not running, a few seconds apart."""
    started, gap = [], 0
    for emu in cfg["emulators"]:
        if emu["enabled"] and not emulator.is_running(emu) and not jobs.busy(emu["id"]):
            start_one(cfg, emu, delay=gap)
            started.append(emu["name"])
            gap += 10
    return started


def stop_one(cfg, emu, force=False):
    jobs.run(emu["id"], emu["name"], "Force stop" if force else "Stop",
             lambda: emulator.stop(cfg, emu, force=force))


def stop_all(cfg):
    stopped = []
    for emu in cfg["emulators"]:
        if emulator.is_running(emu) and not jobs.busy(emu["id"]):
            stop_one(cfg, emu)
            stopped.append(emu["name"])
    return stopped


def reboot_one(cfg, emu):
    def work():
        emulator.reboot(cfg, emu)
        state.forget(config.serial(emu))
        return "booted"
    jobs.run(emu["id"], emu["name"], "Reboot", work)


def reset_one(cfg, emu, typed):
    if typed != emulator.reset_phrase(emu):
        raise emulator.LabError(f"Not reset. Type exactly: {emulator.reset_phrase(emu)}")

    def work():
        emulator.reset(cfg, emu, typed)
        state.forget(config.serial(emu))
        return "wiped and booted"
    jobs.run(emu["id"], emu["name"], "Reset", work)


def open_app(cfg, emu, app_key):
    """Opens the app. If it is not installed, opens its Play Store page so you can install it."""
    app = next((a for a in cfg["apps"] if a["key"] == app_key), None)
    if app is None:
        raise emulator.LabError(f"Unknown app {app_key}")
    serial = config.serial(emu)
    online = adb.devices(cfg)
    if online.get(serial) != "device" or not adb.booted(cfg, serial):
        raise emulator.LabError(f"{emu['name']} is not booted yet.")
    have = adb.installed(cfg, serial, app["packages"])
    if have:
        adb.launch(cfg, serial, have[0])
        jobs.note(f"{emu['name']}: opened {app['label']}")
        return f"Opened {app['label']}"
    others = [s for s, st in online.items() if st == "device" and s != serial]

    def work():
        how = appinstall.ensure(cfg, serial, app, others)
        state.forget(serial)
        adb.launch(cfg, serial, adb.installed(cfg, serial, app["packages"])[0])
        return f"{app['label']} {how}, now open"
    jobs.run(emu["id"], emu["name"], f"Install {app['label']}", work)
    return f"Installing {app['label']} on {emu['name']}… watch it in the phone screen."


def go_all(cfg, app_key="tiktok"):
    """Opens one app (TikTok first by default) on every booted emulator."""
    results = []
    for emu in cfg["emulators"]:
        try:
            results.append(f"{emu['name']}: {open_app(cfg, emu, app_key)}")
        except (emulator.LabError, adb.AdbError, RuntimeError) as exc:
            results.append(f"{emu['name']}: {exc}")
    return results
