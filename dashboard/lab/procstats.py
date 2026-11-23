"""Finds running emulator processes on the PC and measures their CPU and memory use."""
import json
import os
import re
import subprocess
import time

NO_WINDOW = 0x08000000
_PS = ("Get-CimInstance Win32_Process -Filter \"Name like 'qemu-system%' or Name='emulator.exe'\" | "
       "ForEach-Object { [pscustomobject]@{ pid=$_.ProcessId; name=$_.Name; cmd=$_.CommandLine; "
       "ws=$_.WorkingSetSize; cpu=($_.KernelModeTime + $_.UserModeTime)/1e7 } } | ConvertTo-Json -Compress")

_last_cpu = {}  # pid -> (cpu_seconds, wall_time)
_cache = {"time": 0.0, "data": {}}


def _query():
    done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS],
                          capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW)
    text = (done.stdout or "").strip()
    if not text:
        return []
    rows = json.loads(text)
    return rows if isinstance(rows, list) else [rows]


def _avd_of(cmd):
    match = re.search(r"(?:-avd\s+|@)([A-Za-z0-9_.-]+)", cmd or "")
    return match.group(1) if match else None


def snapshot(max_age=2.0):
    """Returns {avd_name: {pids, memMB, cpuPct}} for every running emulator."""
    now = time.time()
    if now - _cache["time"] < max_age:
        return _cache["data"]
    try:
        rows = _query()
    except (subprocess.SubprocessError, ValueError):
        rows = []
    cores = os.cpu_count() or 1
    data = {}
    for row in rows:
        avd = _avd_of(row.get("cmd"))
        if not avd:
            continue
        item = data.setdefault(avd, {"pids": [], "memMB": 0.0, "cpuPct": 0.0, "qemu": False})
        item["pids"].append(row["pid"])
        if row["name"].lower().startswith("qemu-system"):
            item["qemu"] = True
        item["memMB"] += (row.get("ws") or 0) / 1_048_576
        cpu = row.get("cpu") or 0.0
        prev = _last_cpu.get(row["pid"])
        if prev and now > prev[1]:
            item["cpuPct"] += max(0.0, (cpu - prev[0]) / (now - prev[1]) / cores * 100)
        _last_cpu[row["pid"]] = (cpu, now)
    for item in data.values():
        item["memMB"] = round(item["memMB"])
        item["cpuPct"] = round(item["cpuPct"], 1)
    _cache.update(time=now, data=data)
    return data
