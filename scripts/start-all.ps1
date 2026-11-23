# Starts every emulator marked "enabled" in config\lab.json and waits until each has booted.
. "$PSScriptRoot\common.ps1"
exit (Invoke-LabCli @('start-all'))
