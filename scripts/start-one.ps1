# Starts one emulator.  Example:  .\start-one.ps1 -Id 02
param([Parameter(Mandatory = $true)][ValidatePattern('^\d\d$')][string]$Id)
. "$PSScriptRoot\common.ps1"
exit (Invoke-LabCli @('start', $Id))
