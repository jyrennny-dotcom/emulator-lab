@echo off
rem Opens the EMULATOR Start window (START button + link for your friend).
cd /d "%~dp0dashboard"
where pythonw >nul 2>nul && (start "" pythonw hud.pyw) || (start "" python hud.pyw)
