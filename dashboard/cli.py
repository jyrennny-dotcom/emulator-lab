"""Command-line tool behind the PowerShell scripts. Runs everything in the foreground and waits.
Usage: python cli.py create | start-all | stop-all | start ID | stop ID | reset ID | status | friend-key [new]
       python cli.py update "text"   (posts to the live Updates panel your friend sees)"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lab import adb, config, emulator, friendkey, log, state, updates  # noqa: E402


def say(text):
    print(text, flush=True)


def create(cfg):
    for emu in cfg["emulators"]:
        made = emulator.create_avd(cfg, emu)
        say(f"{emu['name']}: {'created' if made else 'already exists, kept as is'}")


def start_list(cfg, emus):
    adb.ensure_server(cfg)
    started = []
    for emu in emus:
        if emulator.is_running(emu):
            say(f"{emu['name']}: already running")
            continue
        try:
            emulator.start(cfg, emu)
            started.append(emu)
            say(f"{emu['name']}: starting on port {emu['port']}")
            time.sleep(8)
        except emulator.LabError as exc:
            say(f"{emu['name']}: FAILED - {exc}")
    failed = 0
    for emu in started:
        try:
            emulator.wait_boot(cfg, emu)
            say(f"{emu['name']}: booted ({config.serial(emu)})")
        except emulator.LabError as exc:
            failed += 1
            say(f"{emu['name']}: FAILED - {exc}")
    return failed


def stop_list(cfg, emus):
    for emu in emus:
        try:
            say(f"{emu['name']}: {emulator.stop(cfg, emu)}")
        except emulator.LabError as exc:
            say(f"{emu['name']}: {exc}")


def reset(cfg, emu):
    phrase = emulator.reset_phrase(emu)
    say(f"This WIPES all apps, logins and data on {emu['name']} only. It cannot be undone.")
    typed = input(f"Type  {phrase}  to confirm (anything else cancels): ").strip()
    if typed != phrase:
        say("Cancelled. Nothing was wiped.")
        return 1
    emulator.reset(cfg, emu, typed)
    say(f"{emu['name']}: wiped and booted.")
    return 0


def status(cfg):
    data = state.build(cfg)
    for line in data["problems"] + ([data["adbError"]] if data["adbError"] else []):
        say(f"! {line}")
    say(f"{'Name':<12} {'Serial':<15} {'Running':<8} {'ADB':<14} {'Booted':<7} {'Android':<8} {'CPU':>6} {'RAM':>8}  Apps")
    for item in data["emulators"]:
        c, lv = item["config"], item["live"]
        apps = ", ".join(f"{k}:{'yes' if v else ('no' if v is False else '?')}" for k, v in lv["appsDetected"].items())
        cpu = f"{lv['cpuPct']}%" if lv["cpuPct"] is not None else "-"
        mem = f"{lv['memMB']}MB" if lv["memMB"] is not None else "-"
        say(f"{c['name']:<12} {lv['serial']:<15} {str(lv['running']):<8} {lv['adb']:<14} {str(lv['booted']):<7} "
            f"{lv['android'] or '-':<8} {cpu:>6} {mem:>8}  {apps}")


def main(argv):
    if not argv:
        say(__doc__)
        return 2
    cfg = config.load()
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "create":
            create(cfg)
        elif cmd == "start-all":
            return start_list(cfg, [e for e in cfg["emulators"] if e["enabled"]])
        elif cmd == "stop-all":
            stop_list(cfg, cfg["emulators"])
        elif cmd == "start":
            return start_list(cfg, [config.find(cfg, rest[0])])
        elif cmd == "stop":
            stop_list(cfg, [config.find(cfg, rest[0])])
        elif cmd == "reset":
            return reset(cfg, config.find(cfg, rest[0]))
        elif cmd == "status":
            status(cfg)
        elif cmd == "friend-key":
            say(friendkey.new() if rest[:1] == ["new"] else friendkey.get())
        elif cmd == "enable-count":  # how many phones "Start all" boots (setup picks it from the PC's RAM)
            count = int(rest[0])
            for i, emu in enumerate(cfg["emulators"]):
                config.save_hardware(emu["id"], {"enabled": i < count})
            say(f"Start all will boot {count} phone(s).")
        elif cmd == "update":
            say(f"Posted: {updates.add(' '.join(rest))['text']}")
        else:
            say(__doc__)
            return 2
    except (emulator.LabError, adb.AdbError, KeyError, IndexError) as exc:
        say(f"Error: {exc}")
        log.error(f"cli {cmd}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
