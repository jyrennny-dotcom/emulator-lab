# Shows each emulator: running, ADB state, booted, Android version, CPU, RAM, TikTok/YouTube installed.
. "$PSScriptRoot\common.ps1"
exit (Invoke-LabCli @('status'))
