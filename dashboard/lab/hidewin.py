"""Hides the windows of running emulators (they keep running), so nothing shows on the owner's screen."""
import ctypes
from ctypes import wintypes

from . import procstats


def hide_all():
    pids = set()
    for info in procstats.snapshot(max_age=0).values():
        pids.update(info["pids"])
    user32 = ctypes.windll.user32
    hidden = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()
        # emulator windows, plus terminal windows Windows opened for an emulator's console
        console = any(t in title for t in ("qemu-system", "\\emulator\\emulator.exe", "cloudflared"))
        if (owner.value in pids or console) and user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, 0)  # SW_HIDE
            hidden.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    return len(hidden)
