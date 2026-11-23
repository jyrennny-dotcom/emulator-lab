# scripts

PowerShell scripts for Windows. All except `setup.ps1` and `share-link.ps1` are thin wrappers around `dashboard/cli.py`.

| File | What it does |
|---|---|
| `common.ps1` | Shared helpers: find Python, write `logs/scripts.log`, start the dashboard |
| `setup.ps1` | Installs Java 17, Android SDK tools, emulator and Android 14 image; creates the emulators |
| `start-all.ps1` / `stop-all.ps1` | Start enabled emulators / stop all |
| `start-one.ps1 -Id NN` | Start one emulator |
| `reset-one.ps1 -Id NN` | Wipe one emulator after typing a confirmation |
| `status.ps1` | Status table |
| `share-link.ps1` | Prints and copies the friend link (the dashboard keeps it open) |
| `autostart.ps1` | Start the dashboard at Windows sign-in (`-Remove` to undo) |
| `desktop-shortcut.ps1` | EMULATOR Start shortcut on the desktop |

If PowerShell refuses to run scripts, start them like this:
`powershell -ExecutionPolicy Bypass -File .\scripts\status.ps1`
