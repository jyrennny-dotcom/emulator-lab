# dashboard

The web dashboard, the START/GO window, and the code that controls the emulators.

| File | What it does |
|---|---|
| `server.py` | Web server: your dashboard on 127.0.0.1:8765, key-protected friend side on 127.0.0.1:8766 |
| `hud.pyw` | EMULATOR Start window: START button, link for your friend with Copy; starts the server if needed |
| `cli.py` | Command-line tool the PowerShell scripts call |
| `lab/config.py` | Reads `config/lab.json`, finds SDK tools, saves hardware changes |
| `lab/adb.py` | adb calls: device list, boot check, installed apps, launch app |
| `lab/emulator.py` | Create, start, stop, reboot, reset one emulator; bring its window forward |
| `lab/actions.py` | Higher-level actions shared by server, HUD and CLI (start all, GO, open app) |
| `lab/jobs.py` | Runs slow actions in the background, one per emulator; live activity feed |
| `lab/state.py` | Builds the live status of every emulator |
| `lab/procstats.py` | CPU and memory use of each emulator process |
| `lab/screen.py` | Phone screen: screenshots, taps, swipes, typing, keys |
| `lab/store.py` | Saves your checklist and notes to `data/status.json` (refuses emails and passwords) |
| `lab/friendkey.py` | Secret key for the friend link |
| `lab/appinstall.py` | Installs TikTok/YouTube: saved copy, copy from another phone, or Play Store Install tap |
| `lab/hidewin.py` | Hides any emulator window so nothing shows on the owner's screen |
| `lab/tunnel.py` | Keeps the friend link open (Cloudflare quick tunnel to port 8766) |
| `lab/updates.py` | "What's new to test" list shown live on the dashboard |
| `lab/log.py` | Writes `logs/lab.log` |
| `static/` | The page: `index.html`, `style.css`, `app.js` (refresh loop), `card.js` (one emulator card), `phone.js`, `dialogs.js`, `api.js` |
