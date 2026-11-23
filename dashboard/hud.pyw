"""EMULATOR Start: a small window. START turns everything on (dashboard, friend link, phones).
Under it is the link to send to your friend, with a Copy button."""
import json
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lab import config  # noqa: E402

CFG = config.load()
BASE = f"http://127.0.0.1:{CFG['dashboardPort']}"
DETACHED = 0x00000008 | 0x00000200
BG, PANEL, TEXT, MUTED = "#0e1116", "#1c232d", "#e6edf3", "#8b98a7"
GREEN, PINK = "#2ea043", "#fe2c55"


def call(path, body=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method="GET" if body is None else "POST",
                                 headers={"Content-Type": "application/json", "X-Lab-Request": "1"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


def server_up():
    try:
        call("/api/state", timeout=8)
        return True
    except Exception:
        return False


def ensure_server():
    if server_up():
        return True
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pyw if pyw.exists() else sys.executable)
    subprocess.Popen([exe, str(HERE / "server.py")], cwd=str(HERE), creationflags=DETACHED)
    for _ in range(30):
        if server_up():
            return True
        threading.Event().wait(0.5)
    return False


class EmulatorStart(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EMULATOR Start")
        self.configure(bg=BG, padx=18, pady=16)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        tk.Label(self, text="EMULATOR Start", fg="#25f4ee", bg=BG, font=("Segoe UI", 15, "bold")).pack()
        self.start_btn = tk.Button(self, text="START", command=self.start, bg=GREEN, fg="white",
                                   activebackground=GREEN, activeforeground="white", relief="flat",
                                   font=("Segoe UI", 16, "bold"), width=16, pady=10, cursor="hand2")
        self.start_btn.pack(pady=(12, 6))
        self.status = tk.Label(self, text="Press START to turn it on.", fg=MUTED, bg=BG,
                               font=("Segoe UI", 9), wraplength=300, justify="center")
        self.status.pack(pady=(0, 12))

        share = tk.Frame(self, bg=BG)  # only shown on a PC that shares its phones through a link
        if CFG.get("autoShare", False):
            share.pack(fill="x")
        tk.Label(share, text="Link for your friend", fg=TEXT, bg=BG, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.link_var = tk.StringVar(value="Press START to make the link")
        self.link_box = tk.Entry(share, textvariable=self.link_var, state="readonly", width=44, relief="flat",
                                 readonlybackground=PANEL, fg=TEXT, font=("Consolas", 9))
        self.link_box.pack(fill="x", ipady=6, pady=(4, 6))
        self.copy_btn = tk.Button(share, text="Copy link", command=self.copy_link, bg=PINK, fg="white",
                                  activebackground=PINK, activeforeground="white", relief="flat",
                                  font=("Segoe UI", 11, "bold"), pady=5, cursor="hand2", state="disabled")
        self.copy_btn.pack(fill="x")
        self.my_stamp = Path(__file__).stat().st_mtime  # an update changed this app: restart it

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", pady=(12, 0))
        for text, cmd in (("Open dashboard", lambda: webbrowser.open(BASE)), ("Stop phones", self.stop_all)):
            tk.Button(row, text=text, command=cmd, bg=PANEL, fg=TEXT, activebackground=PANEL, relief="flat",
                      font=("Segoe UI", 9), pady=4, cursor="hand2").pack(side="left", expand=True, fill="x", padx=2)
        self.link = ""
        self.after(500, self._poll)

    # ---------- helpers ----------
    def say(self, text):
        self.after(0, lambda: self.status.configure(text=text))

    def _bg(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _show_link(self, link, status):
        def apply():
            self.link = link
            self.link_var.set(link or f"Link not ready yet ({status})…")
            self.copy_btn.configure(state="normal" if link else "disabled")
        self.after(0, apply)

    # ---------- live refresh ----------
    def _poll(self):
        def work():
            try:
                state = call("/api/state", timeout=20)
            except Exception:
                return  # not turned on yet
            friend = state.get("friend") or {}
            self._show_link(friend.get("link", ""), friend.get("status", "off"))
            if state["problems"]:
                self.say("Setup needed: double-click INSTALL.bat")
                return
            items = state["emulators"]
            ready = sum(1 for e in items if e["live"]["running"] and e["live"]["booted"])
            booting = sum(1 for e in items if e["live"]["running"]) - ready
            self.say(f"ON  ·  phones: {ready} ready, {booting} starting")
            self.after(0, lambda: self.start_btn.configure(text="RUNNING ✓" if ready or booting else "START"))

        def again():
            if Path(__file__).stat().st_mtime != self.my_stamp:  # updated: reopen the new version
                subprocess.Popen([sys.executable, str(Path(__file__))], cwd=str(HERE))
                self.destroy()
                return
            self._bg(work)
            self.after(3000, again)
        again()

    # ---------- buttons ----------
    def start(self):
        def work():
            self.say("Turning on…")
            if not ensure_server():
                self.say("Could not turn on. See logs\\lab.log")
                return
            try:
                started = call("/api/start-all", {})["result"]
                self.say("Starting " + ", ".join(started) + "…" if started else "Already on.")
            except Exception as exc:
                self.say(f"Start failed: {exc}")
        self._bg(work)

    def copy_link(self):
        if self.link:
            self.clipboard_clear()
            self.clipboard_append(self.link)
            self.say("Link copied. Paste it to your friend.")

    def stop_all(self):
        def work():
            try:
                stopped = call("/api/stop-all", {})["result"]
                self.say("Stopping " + ", ".join(stopped) + "…" if stopped else "No phones running.")
            except Exception:
                self.say("Not turned on.")
        self._bg(work)


if __name__ == "__main__":
    EmulatorStart().mainloop()
