# One-time setup: Python, Java, Android SDK tools, Android 14 Google Play image, and the five emulators.
# Safe to run again: it skips what is already there and never deletes emulator data.
#   -Yes          answer yes to every install question (used by INSTALL.bat)
#   -NoShortcut   do not put an "EMULATOR Start" shortcut on the desktop
param([switch]$Yes, [switch]$NoShortcut)
. "$PSScriptRoot\common.ps1"

function Say($text, $color = 'Gray') { Write-Host $text -ForegroundColor $color }
function Ask($question) {
    if ($Yes) { Say "$question  -> yes"; return $true }
    (Read-Host "$question (y/n)").Trim().ToLower() -eq 'y'
}
. "$PSScriptRoot\prereqs.ps1"

Say "== Android Emulator Lab setup ==" Cyan
Say "Lab folder: $LabRoot"
Say "SDK folder: $SdkRoot"

# 1. Space, Python, Java
$ramGB = Test-LabSpace
$py = Install-LabPython
Say "Python: $py" Green
$env:JAVA_HOME = Install-LabJava
Say "Java: $env:JAVA_HOME" Green

# 2. Android command-line tools
$sdkManager = Join-Path $SdkRoot 'cmdline-tools\latest\bin\sdkmanager.bat'
if (-not (Test-Path $sdkManager)) {
    Say "Android command-line tools are missing. They come from Google (dl.google.com, about 150 MB)."
    if (-not (Ask "Download them now?")) { throw "Setup stopped: Android command-line tools are required." }
    $repo = 'https://dl.google.com/android/repository/'
    $zipName = 'commandlinetools-win-13114758_latest.zip'
    $sha1 = $null
    try {
        [xml]$xml = (Invoke-WebRequest -UseBasicParsing "$($repo)repository2-3.xml").Content
        $pkg = $xml.SelectNodes('//remotePackage') | Where-Object { $_.path -eq 'cmdline-tools;latest' } | Select-Object -First 1
        $arc = $pkg.archives.archive | Where-Object { $_.'host-os' -eq 'windows' } | Select-Object -First 1
        $zipName = $arc.complete.url
        $sha1 = $arc.complete.checksum.'#text'
        if (-not $sha1) { $sha1 = $arc.complete.checksum }
    } catch { Say "Could not read Google's package list, using the known file name." Yellow }
    $tmp = Join-Path $env:TEMP "lab-cmdline-tools"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip = Join-Path $tmp $zipName
    Say "Downloading $zipName ..."
    Invoke-WebRequest -UseBasicParsing "$repo$zipName" -OutFile $zip
    if ($sha1) {
        $got = (Get-FileHash $zip -Algorithm SHA1).Hash.ToLower()
        if ($got -ne $sha1.ToLower()) { throw "Download check failed (SHA-1 mismatch). Nothing was installed." }
        Say "Download checked (SHA-1 matches Google's list)." Green
    }
    $unpack = Join-Path $tmp 'unpacked'
    if (Test-Path $unpack) { Remove-Item $unpack -Recurse -Force }
    Expand-Archive $zip -DestinationPath $unpack
    New-Item -ItemType Directory -Force -Path (Join-Path $SdkRoot 'cmdline-tools') | Out-Null
    Move-Item (Join-Path $unpack 'cmdline-tools') (Join-Path $SdkRoot 'cmdline-tools\latest')
}
Say "Command-line tools: OK" Green

# 3. Packages. Newer tools ship Google's "android" CLI (package names use /), older ones only sdkmanager (names use ;)
$packages = @('platform-tools', 'emulator', $LabConfig.platform, $LabConfig.systemImage)
$imageDir = Join-Path $SdkRoot ($LabConfig.systemImage -replace ';', '\')
$have = (Test-Path (Join-Path $SdkRoot 'platform-tools\adb.exe')) -and (Test-Path (Join-Path $SdkRoot 'emulator\emulator.exe')) `
    -and (Test-Path (Join-Path $imageDir 'system.img'))
if ($have) {
    Say "Android packages: already installed" Green
} else {
    Say "`nInstalling: $($packages -join ', ')  (about 2.5 GB the first time, this takes a while)" Cyan
    Say "By installing these you accept Google's Android SDK terms: https://developer.android.com/studio/terms"
    $androidCli = Join-Path $SdkRoot 'cmdline-tools\latest\bin\android.exe'
    if (Test-Path $androidCli) {
        $names = $packages | ForEach-Object { $_ -replace ';', '/' }
        & $androidCli --no-metrics --sdk="$SdkRoot" sdk install @names
    } else {
        Say "Google's SDK licences come next. Read them and answer y to accept." Cyan
        & $sdkManager --sdk_root="$SdkRoot" --licenses
        # cmd splits words at ';', so each package name must be quoted for the .bat file
        $quoted = $packages | ForEach-Object { "`"$_`"" }
        & $sdkManager --sdk_root="$SdkRoot" @quoted
    }
    if ($LASTEXITCODE -ne 0) { throw "Installing SDK packages failed (exit $LASTEXITCODE). See the messages above." }
    if (-not (Test-Path (Join-Path $imageDir 'system.img'))) {
        throw "The system image $($LabConfig.systemImage) is still missing after installing. See the messages above."
    }
}

# 4. Make the emulators (existing ones are kept as they are)
$env:ANDROID_SDK_ROOT = $SdkRoot
$env:ANDROID_HOME = $SdkRoot
Say "`nCreating emulators..." Cyan
if ((Invoke-LabCli @('create')) -ne 0) { throw "Creating the emulators failed. See the messages above." }
Set-LabEmulatorCount $ramGB

# 5. Acceleration check, desktop shortcut
$accelOk = Test-LabAcceleration
if (-not $NoShortcut) { New-LabShortcut }

Write-LabLog 'setup finished'
if ($accelOk) {
    Say "`nSetup finished. Open 'EMULATOR Start' on the desktop and press START." Green
} else {
    Say "`nSetup finished, but fix hardware acceleration (see above) before starting the emulators." Yellow
}
