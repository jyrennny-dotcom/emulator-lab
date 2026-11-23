# Android Emulator Lab

Android 14 phones (with Google Play) on your Windows PC for testing TikTok and YouTube, with a simple START window and a dashboard.

## Install (do this once)

1. **Download:** [click here to download the ZIP](https://github.com/jyrennny-dotcom/emulator-lab/archive/refs/heads/main.zip).
2. **Unzip it:** right-click the ZIP > **Extract All** > pick a folder you'll keep (for example Documents) > Extract.
3. **Install:** open the folder and double-click **INSTALL.bat**. Click **Yes** whenever Windows asks. It downloads about 3 GB and takes 20–40 minutes.
4. **Use it:** open **EMULATOR Start** on your desktop and press **START**. The phones open in their own windows.

It updates itself: every 5 minutes it checks for a newer version and installs it, while it's running. You never need to download it again.

Needs: Windows 10/11, 16 GB RAM or more is best, about 15 GB free disk space.

Something not working? Send a screenshot of the window, plus the `logs` folder inside the install folder.

## Details

## First time (manual way)

1. Open PowerShell in this folder and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
   ```
   It installs Java 17 (if missing), Google's Android SDK tools, the emulator and the Android 14 Google Play image (about 2.5 GB), and asks you to accept Google's SDK licences. Then it creates Emulator 01–05. Running it again is safe: nothing that exists is deleted.
2. Double-click **EMULATOR Start** on your desktop (or `Start-Lab.bat`). A small window opens:
   - **START** turns everything on: the dashboard, the friend link, and every enabled emulator (01–03 by default).
   - Under it is the **link for your friend**, with a **Copy link** button.
   - **Open dashboard** and **Stop phones** sit at the bottom.
   The dashboard and friend link also start by themselves when Windows starts (`scripts\autostart.ps1`; turn off with `-Remove`).
3. On each emulator, sign in to Google Play **by hand**, install TikTok from the Play Store, and log in to TikTok / YouTube **by hand**. YouTube comes with the Google Play image.

## The emulators

| Name | AVD | ADB serial | In "Start all" |
|---|---|---|---|
| Emulator 01 | Lab_Emulator_01 | emulator-5554 | yes |
| Emulator 02 | Lab_Emulator_02 | emulator-5556 | yes |
| Emulator 03 | Lab_Emulator_03 | emulator-5558 | yes |
| Emulator 04 | Lab_Emulator_04 | emulator-5560 | no (turn on in Hardware) |
| Emulator 05 | Lab_Emulator_05 | emulator-5562 | no (turn on in Hardware) |

Each one has its own storage, app data and device profile (Pixel 7, 3 GB RAM, 4 cores, 1080×2400, 420 dpi). Change RAM, cores, resolution and DPI in the dashboard's **Hardware** box or in `config/lab.json`. Data stays between sessions: Stop shuts down cleanly and keeps everything.

## Dashboard (http://127.0.0.1:8765)

Start, stop, force-stop, reboot, open TikTok / YouTube, phone screen in the browser, bring the emulator window to the front, copy the ADB serial, reconnect offline ADB devices, CPU and memory use, and reset **one** emulator (you must type `RESET Emulator 0X`; there is no reset-all anywhere). If TikTok is not installed, "Open TikTok" opens its Play Store page so you can install it.

The **Checklist & notes** part of each card is filled in by you and saved to `data/status.json`: nickname, account label (nickname only; emails are refused), TikTok and YouTube checks (installed, logged in, Rewards tab, invite screen, invite link), date last checked, notes, testing status. Notes that look like passwords or codes are refused.

## Friend link

The dashboard opens the friend link by itself whenever it runs. Click **Copy friend link** on the dashboard or **Friend link** in the START/GO window, and paste it to your friend. He gets the same dashboard and phone screens, live, plus an **Updates** panel listing what's new to test. The address changes each time the dashboard restarts, so send the new one after a restart. See `docs/friend-link.md`.

Post an update to that panel: `python dashboard\cli.py update "what changed"`.

Nothing shows on the owner's screen: phones run hidden (`"showWindows": false` in `config/lab.json`) and are used through **Phone screen** on the dashboard. When the dashboard's code changes it restarts itself within seconds and keeps the same friend link; open pages reload themselves.

**Open TikTok** installs TikTok when it is missing: from a saved copy, by copying it from another phone that has it, or through the Play Store (someone must sign in to Google on that phone once, by hand).

## Scripts (PowerShell, in `scripts/`)

| Script | What it does |
|---|---|
| `setup.ps1` | One-time install and emulator creation |
| `start-all.ps1` | Start enabled emulators and wait until booted |
| `stop-all.ps1` | Stop all emulators cleanly |
| `start-one.ps1 -Id 02` | Start one emulator |
| `reset-one.ps1 -Id 02` | Wipe one emulator after typed confirmation |
| `status.ps1` | Table of every emulator's state |
| `share-link.ps1 [-NewKey]` | Friend link; `-NewKey` cuts off old links |
| `autostart.ps1 [-Remove]` | Start the dashboard and friend link when Windows starts |
| `desktop-shortcut.ps1` | Put the EMULATOR Start shortcut on the desktop |

## Logs

`logs/lab.log` (starts, stops, reboots, resets, errors), `logs/emulator-0X.log` (each emulator's own output), `logs/scripts.log`, `logs/tunnel.log`.

## What this project will not do

No account creation, no automated sign-ins, no referral or invite automation, no reading tokens or private app data, no device-fingerprint spoofing. Credentials never go in any file.
