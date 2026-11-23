"""Phone screen in the browser: takes a screenshot and sends taps, swipes, typing and keys."""
import re
import subprocess

from . import adb, config

NO_WINDOW = 0x08000000
KEYS = {"back": 4, "home": 3, "recents": 187, "enter": 66, "delete": 67,
        "volup": 24, "voldown": 25, "power": 26}


def screenshot(cfg, emu):
    """Returns PNG bytes of the emulator's screen."""
    exe = config.adb_exe(cfg)
    done = subprocess.run([str(exe), "-s", config.serial(emu), "exec-out", "screencap", "-p"],
                          capture_output=True, timeout=15, creationflags=NO_WINDOW)
    if done.returncode != 0 or not done.stdout.startswith(b"\x89PNG"):
        raise adb.AdbError(f"Could not read the screen of {emu['name']}.")
    return done.stdout


def _num(value, low=0, high=10000):
    num = int(float(value))
    if not low <= num <= high:
        raise ValueError("Position is off the screen.")
    return num


def send(cfg, emu, body):
    """body: {type: tap|swipe|text|key, x, y, x2, y2, text, key}. Positions are screen pixels."""
    serial = config.serial(emu)
    kind = body.get("type")
    if kind == "tap":
        cmd = f"input tap {_num(body['x'])} {_num(body['y'])}"
    elif kind == "swipe":
        ms = _num(body.get("ms", 300), 50, 3000)
        cmd = (f"input swipe {_num(body['x'])} {_num(body['y'])} "
               f"{_num(body['x2'])} {_num(body['y2'])} {ms}")
    elif kind == "text":
        text = str(body.get("text", ""))[:200]
        if not text:
            return
        # adb's input text needs spaces as %s and only plain characters
        safe = re.sub(r"[^A-Za-z0-9 .,!?@_\-:/]", "", text).replace(" ", "%s")
        cmd = f"input text '{safe}'"
    elif kind == "key":
        code = KEYS.get(body.get("key"))
        if code is None:
            raise ValueError("Unknown key")
        cmd = f"input keyevent {code}"
    else:
        raise ValueError("Unknown input type")
    adb.shell(cfg, serial, cmd)
