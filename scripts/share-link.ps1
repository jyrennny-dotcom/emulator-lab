# Prints the friend link and copies it. The dashboard keeps the link open by itself (dashboard\lab\tunnel.py).
# First time: offers to install Cloudflare's free 'cloudflared' tunnel tool.
# -NewKey makes a new secret key, so every old link stops working.
param([switch]$NewKey)
. "$PSScriptRoot\common.ps1"

$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf -and -not (Test-Path "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe") -and
    -not (Test-Path "$env:ProgramFiles\cloudflared\cloudflared.exe")) {
    Write-Host "Sharing needs 'cloudflared' (Cloudflare's free tunnel tool, about 20 MB, installed with winget)." -ForegroundColor Yellow
    if ((Read-Host "Install it now? (y/n)").Trim().ToLower() -ne 'y') { exit 1 }
    winget install --id Cloudflare.cloudflared -e --source winget
    Write-Host "Installed. Close the dashboard (or restart the PC) so it picks cloudflared up." -ForegroundColor Yellow
}

if ($NewKey) {
    $py = Get-LabPython
    & $py "$LabCli" friend-key new | Out-Null
    Write-Host "Made a new key. Old friend links no longer work." -ForegroundColor Yellow
}

Start-LabDashboard
$link = ''
for ($i = 0; $i -lt 60 -and -not $link; $i++) {
    $state = Invoke-RestMethod "http://127.0.0.1:$($LabConfig.dashboardPort)/api/state" -TimeoutSec 20
    $link = $state.friend.link
    if (-not $link) { Start-Sleep -Seconds 1 }
}
if (-not $link) { throw "The friend link is not ready after 60 seconds. See $LabRoot\logs\tunnel.log" }
Set-Clipboard -Value $link
Write-Host "Friend link (copied):" -ForegroundColor Green
Write-Host "  $link"
Write-Host "It stays open while the dashboard runs. The address changes each time the dashboard restarts."
