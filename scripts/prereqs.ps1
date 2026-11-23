# Checks and installs what a fresh PC needs: Python, Java 17, disk space, hardware acceleration.
# Dot-sourced by setup.ps1 after common.ps1. Uses Say and Ask from setup.ps1.

function Install-LabPython {
    try { return Get-LabPython } catch { }
    Say "Python 3 is needed and is not installed. It will be installed with winget (python.org build, about 30 MB)." Yellow
    if (-not (Ask "Install Python now?")) { throw "Setup stopped: Python 3 is required." }
    winget install --id Python.Python.3.12 -e --scope user --source winget --accept-package-agreements
    return Get-LabPython
}

function Find-LabJava {
    if ($env:JAVA_HOME -and (Test-Path "$env:JAVA_HOME\bin\java.exe")) { return $env:JAVA_HOME }
    $roots = @("$env:ProgramFiles\Eclipse Adoptium", "$env:ProgramFiles\Microsoft", "$env:ProgramFiles\Java",
               "$env:ProgramFiles\Android\Android Studio")
    foreach ($root in $roots) {
        if (Test-Path $root) {
            $hit = Get-ChildItem $root -Recurse -Filter java.exe -Depth 3 -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -match 'jdk-(1[7-9]|2\d)|jbr' } | Select-Object -First 1
            if ($hit) { return (Split-Path (Split-Path $hit.FullName)) }
        }
    }
    return $null
}

function Install-LabJava {
    $java = Find-LabJava
    if ($java) { return $java }
    Say "Java 17 is needed by Google's SDK tools and is not installed." Yellow
    Say "It will be installed with winget: Eclipse Temurin 17 JDK (from adoptium.net, about 190 MB)."
    if (-not (Ask "Install Java 17 now?")) { throw "Setup stopped: Java 17 is required." }
    winget install --id EclipseAdoptium.Temurin.17.JDK -e --source winget --accept-package-agreements
    $java = Find-LabJava
    if (-not $java) { throw "Java was not found after installing. Close this window, open a new one and run setup again." }
    return $java
}

function Test-LabSpace {
    $drive = (Split-Path -Qualifier $SdkRoot).TrimEnd(':')
    $freeGB = [math]::Round((Get-PSDrive $drive).Free / 1GB)
    $ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
    Say "Free space on ${drive}: $freeGB GB.  RAM: $ramGB GB."
    if ($freeGB -lt 15) {
        Say "Less than 15 GB free. The Android tools and emulators need about 12 GB. Free up space first." Yellow
        if (-not (Ask "Continue anyway?")) { throw "Setup stopped: not enough disk space." }
    }
    return $ramGB
}

# Picks how many emulators "Start all" boots, so a smaller PC is not overloaded.
function Set-LabEmulatorCount([int]$ramGB) {
    $count = if ($ramGB -ge 24) { 3 } elseif ($ramGB -ge 14) { 2 } else { 1 }
    Say "This PC has $ramGB GB RAM, so 'Start all' will boot $count emulator(s). Change it any time in the dashboard (Hardware)."
    Invoke-LabCli @('enable-count', "$count") | Out-Null
}

function Test-LabAcceleration {
    $emu = Join-Path $SdkRoot 'emulator\emulator.exe'
    $out = & $emu -accel-check 2>&1 | Out-String
    if ($out -match 'is installed and usable') { Say "Hardware acceleration: OK" Green; return $true }
    Say "Hardware acceleration is not working. Emulators will not start without it." Yellow
    Say $out
    Say "Fix: turn on 'Windows Hypervisor Platform' (needs admin, then a restart)." Yellow
    if (Ask "Turn it on now? Windows will ask for admin permission.") {
        Start-Process powershell -Verb RunAs -Wait -ArgumentList @('-NoProfile', '-Command',
            'Enable-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -All -NoRestart')
        Say "Done. RESTART the PC, then open Emulator Lab from the desktop." Yellow
    }
    Say "If it still fails after a restart, virtualization (Intel VT-x / AMD SVM) is off in the BIOS." Yellow
    return $false
}

function New-LabShortcut {
    & "$PSScriptRoot\desktop-shortcut.ps1"  # "EMULATOR Start" on the desktop
}
