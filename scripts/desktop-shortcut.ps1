# Puts an "EMULATOR Start" shortcut on your desktop that opens the START window (dashboard\hud.pyw).
. "$PSScriptRoot\common.ps1"

$py = Get-LabPython
$pyw = Join-Path (Split-Path $py) 'pythonw.exe'
if (-not (Test-Path $pyw)) { $pyw = $py }
$desktop = [Environment]::GetFolderPath('Desktop')
$path = Join-Path $desktop 'EMULATOR Start.lnk'

$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($path)
$link.TargetPath = $pyw
$link.Arguments = "`"$(Join-Path $LabRoot 'dashboard\hud.pyw')`""
$link.WorkingDirectory = Join-Path $LabRoot 'dashboard'
$link.Description = 'EMULATOR Start: turn the emulators on and get the link for your friend'
$link.Save()
Write-LabLog "desktop shortcut: $path"
Write-Host "Made $path" -ForegroundColor Green
