"""Builds the live picture of every emulator: running, adb, booted, Android version, apps, CPU, RAM."""
import time
from concurrent.futures import ThreadPoolExecutor

from . import adb, config, jobs, procstats, store, updates

_slow_cache = {}  # serial -> (time, {"android": str, "apps": {...}})


def _device_details(cfg, serial):
    hit = _slow_cache.get(serial)
    if hit and time.time() - hit[0] < 20:
        return hit[1]
    details = {"android": adb.getprop(cfg, serial, "ro.build.version.release"), "apps": {}}
    for app in cfg["apps"]:
        details["apps"][app["key"]] = bool(adb.installed(cfg, serial, app["packages"]))
    _slow_cache[serial] = (time.time(), details)
    return details


def forget(serial):
    _slow_cache.pop(serial, None)


def _one(cfg, emu, adb_states, procs):
    serial = config.serial(emu)
    proc = procs.get(emu["avd"]) or {}
    live = {
        "serial": serial,
        "created": config.avd_dir(emu).exists(),
        "running": bool(proc.get("pids")),
        "adb": adb_states.get(serial, "not connected"),
        "booted": False,
        "android": "",
        "appsDetected": {a["key"]: None for a in cfg["apps"]},
        "cpuPct": proc.get("cpuPct"),
        "memMB": proc.get("memMB"),
    }
    if live["adb"] == "device":
        try:
            live["booted"] = adb.booted(cfg, serial)
            if live["booted"]:
                details = _device_details(cfg, serial)
                live["android"] = details["android"]
                live["appsDetected"] = details["apps"]
        except adb.AdbError as exc:
            live["adbError"] = str(exc)
    if live["running"] and live["adb"] == "offline":
        live["warning"] = "ADB says offline. Try Reconnect ADB, or Reboot."
    return live


def build(cfg):
    problems = config.missing_deps(cfg)
    adb_states, adb_error = {}, ""
    if config.adb_exe(cfg).exists():
        try:
            adb_states = adb.devices(cfg)
        except adb.AdbError as exc:
            adb_error = str(exc)
    procs = procstats.snapshot()
    tracking = store.load_all(cfg)
    with ThreadPoolExecutor(max_workers=5) as pool:
        lives = list(pool.map(lambda e: _one(cfg, e, adb_states, procs), cfg["emulators"]))
    emulators = []
    for emu, live in zip(cfg["emulators"], lives):
        emulators.append({"config": emu, "live": live, "tracking": tracking[emu["id"]],
                          "job": jobs.current(emu["id"])})
    return {"problems": problems, "adbError": adb_error, "apps": cfg["apps"],
            "checks": store.APP_CHECKS, "testStates": store.TEST_STATES,
            "emulators": emulators, "feed": list(jobs.feed)[:20], "updates": updates.load(),
            "time": time.strftime("%H:%M:%S")}
