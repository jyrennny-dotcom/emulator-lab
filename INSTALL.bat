@echo off
title Emulator Lab - install
echo.
echo  Emulator Lab installer
echo  ---------------------
echo  This installs everything the phones need (Python, Java, Google's Android tools,
echo  Android 14 with Google Play) and makes 5 phones. It downloads about 3 GB and
echo  can take 20-40 minutes. Windows may ask for permission a few times: click Yes.
echo  When it finishes, open "EMULATOR Start" on your desktop and press START.
echo.
pause
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1" -Yes
echo.
echo  Done. If something went wrong, send a screenshot of this window.
pause
