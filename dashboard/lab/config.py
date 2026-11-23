"""Loads config/lab.json and finds the SDK tools. Saves hardware edits back to the config."""
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "config" / "lab.json"
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"

HARDWARE_LIMITS = {
    "ramMB": (1536, 8192),
    "cores": (1, 8),
    "width": (480, 2160),
    "height": (800, 3840),
    "dpi": (120, 640),
}


LOCAL_FILE = DATA_DIR / "settings.json"  # this PC only; never published or overwritten by updates


def load():
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))  # -sig: tolerates Notepad/PowerShell BOMs
    if LOCAL_FILE.exists():
        cfg.update({k: v for k, v in json.loads(LOCAL_FILE.read_text(encoding="utf-8-sig")).items()
                    if k != "emulators"})
    cfg["sdkRoot"] = os.path.expandvars(cfg["sdkRoot"])
    return cfg


def save_hardware(emu_id, values):
    """Change RAM, cores, resolution or DPI for one emulator. Returns the new entry."""
    raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
    entry = next((e for e in raw["emulators"] if e["id"] == emu_id), None)
    if entry is None:
        raise KeyError(f"No emulator with id {emu_id}")
    for key, (low, high) in HARDWARE_LIMITS.items():
        if key in values:
            num = int(values[key])
            if not low <= num <= high:
                raise ValueError(f"{key} must be between {low} and {high}")
            entry[key] = num
    if "enabled" in values:
        entry["enabled"] = bool(values["enabled"])
    shutil.copyfile(CONFIG_FILE, CONFIG_FILE.with_suffix(".json.bak"))
    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_FILE)
    return entry


def find(cfg, emu_id):
    for emu in cfg["emulators"]:
        if emu["id"] == emu_id:
            return emu
    raise KeyError(f"No emulator with id {emu_id}")


def serial(emu):
    return f"emulator-{emu['port']}"


def sdk(cfg, *parts):
    return Path(cfg["sdkRoot"]).joinpath(*parts)


def adb_exe(cfg):
    return sdk(cfg, "platform-tools", "adb.exe")


def emulator_exe(cfg):
    return sdk(cfg, "emulator", "emulator.exe")


def avdmanager_bat(cfg):
    return sdk(cfg, "cmdline-tools", "latest", "bin", "avdmanager.bat")


def system_image_dir(cfg):
    return sdk(cfg, *cfg["systemImage"].split(";"))


def avd_home():
    env = os.environ.get("ANDROID_AVD_HOME")
    return Path(env) if env else Path.home() / ".android" / "avd"


def avd_dir(emu):
    return avd_home() / f"{emu['avd']}.avd"


def missing_deps(cfg):
    """Readable list of what is missing. Empty list means ready."""
    problems = []
    if not Path(cfg["sdkRoot"]).exists():
        problems.append(f"Android SDK not found at {cfg['sdkRoot']}. Run scripts\\setup.ps1.")
        return problems
    if not adb_exe(cfg).exists():
        problems.append("adb (platform-tools) is missing. Run scripts\\setup.ps1.")
    if not emulator_exe(cfg).exists():
        problems.append("Android Emulator is missing. Run scripts\\setup.ps1.")
    if not system_image_dir(cfg).exists():
        problems.append(f"System image {cfg['systemImage']} is missing. Run scripts\\setup.ps1.")
    missing_avds = [e["name"] for e in cfg["emulators"] if not avd_dir(e).exists()]
    if missing_avds:
        problems.append("Not created yet: " + ", ".join(missing_avds) + ". Run scripts\\setup.ps1.")
    return problems
