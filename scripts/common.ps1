# Shared helpers for the lab scripts. Dot-source it:  . "$PSScriptRoot\common.ps1"
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # PowerShell 5.1's progress bar makes downloads many times slower
$LabRoot = Split-Path -Parent $PSScriptRoot
$LabCli = Join-Path $LabRoot 'dashboard\cli.py'
$LabConfig = Get-Content (Join-Path $LabRoot 'config\lab.json') -Raw | ConvertFrom-Json
$SdkRoot = [Environment]::ExpandEnvironmentVariables($LabConfig.sdkRoot)

function Get-LabPython {
    foreach ($name in 'python', 'py') {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { return $cmd.Source }
    }
    # Just installed and PATH not refreshed yet: look in the usual install folders
    $found = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:ProgramFiles\Python3*\python.exe" `
        -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if ($found) { return $found.FullName }
    throw "Python 3 is not installed. Install it from python.org (tick 'Add python.exe to PATH'), then run this again."
}

function Write-LabLog([string]$Message) {
    $dir = Join-Path $LabRoot 'logs'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Add-Content -Path (Join-Path $dir 'scripts.log') -Value "$(Get-Date -Format s) $Message" -Encoding utf8
}

function Invoke-LabCli([string[]]$CliArgs) {
    $py = Get-LabPython
    Write-LabLog "cli $($CliArgs -join ' ')"
    # Start-Process keeps the console (and typing for reset) attached and returns only the exit code
    $argList = @("`"$LabCli`"") + $CliArgs
    $proc = Start-Process -FilePath $py -ArgumentList $argList -NoNewWindow -Wait -PassThru
    return $proc.ExitCode
}

function Test-LabDashboard {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$($LabConfig.dashboardPort)/api/state" | Out-Null
        return $true
    } catch { return $false }
}

function Start-LabDashboard {
    if (Test-LabDashboard) { return }
    $py = Get-LabPython
    $pyw = Join-Path (Split-Path $py) 'pythonw.exe'
    if (-not (Test-Path $pyw)) { $pyw = $py }
    Start-Process -FilePath $pyw -ArgumentList "`"$(Join-Path $LabRoot 'dashboard\server.py')`"" -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-LabDashboard) { Write-LabLog 'dashboard started'; return }
    }
    throw "The dashboard did not start. See $LabRoot\logs\lab.log"
}
