# Starts the dashboard (and so the friend link) by itself when you sign in to Windows.
# Adds a shortcut to your own Startup folder. No admin rights, no system settings.
#   .\autostart.ps1          turn auto-start on
#   .\autostart.ps1 -Remove  turn it off again
param([switch]$Remove)
. "$PSScriptRoot\common.ps1"

$startup = [Environment]::GetFolderPath('Startup')
$shortcut = Join-Path $startup 'Emulator Lab Dashboard.lnk'

if ($Remove) {
    if (Test-Path $shortcut) {
        Remove-Item -LiteralPath $shortcut -Confirm:$false
        Write-LabLog 'autostart removed'
        Write-Host 'Auto-start is off.' -ForegroundColor Green
    } else {
        Write-Host 'Auto-start was already off.'
    }
    exit 0
}

$py = Get-LabPython
$pyw = Join-Path (Split-Path $py) 'pythonw.exe'
if (-not (Test-Path $pyw)) { $pyw = $py }
$server = Join-Path $LabRoot 'dashboard\server.py'

$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcut)
$link.TargetPath = $pyw
$link.Arguments = "`"$server`""
$link.WorkingDirectory = Join-Path $LabRoot 'dashboard'
$link.Description = 'Emulator Lab dashboard and friend link'
$link.WindowStyle = 7  # minimised; pythonw shows no window anyway
$link.Save()
Write-LabLog "autostart on: $shortcut"
Write-Host "Auto-start is on. Shortcut: $shortcut" -ForegroundColor Green
Write-Host 'The friend link gets a new address after each restart: send the new one with "Copy friend link".'
