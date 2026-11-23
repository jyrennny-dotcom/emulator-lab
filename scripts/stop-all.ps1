# Shuts every running lab emulator down cleanly. App data is kept.
. "$PSScriptRoot\common.ps1"
exit (Invoke-LabCli @('stop-all'))
