# Wipes ONE emulator (apps, logins, data). Asks you to type a confirmation first.
# There is deliberately no "reset all" script.   Example:  .\reset-one.ps1 -Id 03
param([Parameter(Mandatory = $true)][ValidatePattern('^\d\d$')][string]$Id)
. "$PSScriptRoot\common.ps1"
exit (Invoke-LabCli @('reset', $Id))
