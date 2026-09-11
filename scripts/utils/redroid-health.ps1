<#
.SYNOPSIS
    Redroid Comprehensive Health Check Script
.DESCRIPTION
    Validates WSL2, custom kernel BinderFS, Docker Engine, Container lifecycle, ADB, and Android runtime.
.EXAMPLE
    .\redroid-health.ps1 01
#>

param(
    [Parameter(Position=0, Mandatory=$false)]
    [string]$Account = "01"
)

$AccountNum = [int]$Account
$HostPort = 5800 + $AccountNum
$ContainerName = "redroid-$Account"
$VolumeName = "redroid-account-$Account-data"
$AdbTarget = "127.0.0.1:$HostPort"

$ToolsDir = "C:\Users\Shahid\tools\scrcpy"
$AdbExe = Join-Path $ToolsDir "adb.exe"

if (-not (Test-Path $AdbExe)) {
    $foundAdb = Get-Command adb -ErrorAction SilentlyContinue
    if ($foundAdb) { $AdbExe = $foundAdb.Source }
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "         REDROID HEALTH CHECK REPORT (Account $Account)           " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$allPass = $true

function Report-Check {
    param([string]$Title, [bool]$Success, [string]$Details = "")
    if ($Success) {
        Write-Host " [PASS] $Title" -ForegroundColor Green
        if ($Details) { Write-Host "        $Details" -ForegroundColor DarkGray }
    } else {
        Write-Host " [FAIL] $Title" -ForegroundColor Red
        if ($Details) { Write-Host "        $Details" -ForegroundColor Yellow }
        $script:allPass = $false
    }
}

# 1. Check WSL2
$wslUname = (wsl -d Ubuntu -u root -e uname -r 2>$null)
if ($wslUname) {
    Report-Check "WSL2 Ubuntu is Running" $true "Kernel: $wslUname"
} else {
    Report-Check "WSL2 Ubuntu is Running" $false "Could not connect to WSL2 Ubuntu"
}

# 2. Check Binder / BinderFS
$binderCheck = wsl -d Ubuntu -u root -e bash -c "ls -la /dev/binder /dev/binderfs 2>/dev/null | grep -E 'binder|hwbinder|vndbinder' | wc -l" 2>$null
if ([int]$binderCheck -ge 3) {
    Report-Check "Android Binder/BinderFS Active" $true "Character devices /dev/binder, /dev/hwbinder, /dev/vndbinder ready"
} else {
    Report-Check "Android Binder/BinderFS Active" $false "Binder devices not found in /dev"
}

# 3. Check Docker Engine
$dockerVer = wsl -d Ubuntu -u root -e docker --version 2>$null
$dockerActive = wsl -d Ubuntu -u root -e systemctl is-active docker 2>$null
if ($dockerActive -eq "active") {
    Report-Check "Docker Daemon is Active" $true "$dockerVer"
} else {
    Report-Check "Docker Daemon is Active" $false "Docker service status: $dockerActive"
}

# 4. Check Container Exists & Running
$containerStatus = wsl -d Ubuntu -u root -e docker ps -a -f "name=^/${ContainerName}$" --format "{{.Status}}" 2>$null
if ($containerStatus -like "Up*") {
    Report-Check "Redroid Container is Running" $true "Name: $ContainerName ($containerStatus)"
} elseif ($containerStatus) {
    Report-Check "Redroid Container Exists" $true "Status: $containerStatus (Stopped)"
    Report-Check "Redroid Container Running" $false "Container is currently stopped"
} else {
    Report-Check "Redroid Container Exists" $false "Container $ContainerName has not been created yet"
}

# 5. Check ADB Connection
& $AdbExe connect $AdbTarget | Out-Null
$adbDevices = (& $AdbExe devices) -join "`n"
if ($adbDevices -match "$AdbTarget\s+device") {
    Report-Check "ADB Connection Reachable" $true "Target: $AdbTarget (State: device)"
} else {
    Report-Check "ADB Connection Reachable" $false "ADB Target $AdbTarget not found in adb devices"
}

# 6. Check Android Runtime Metrics
$bootComplete = $null
$androidVer = $null
for ($i = 1; $i -le 6; $i++) {
    $androidVer = (& $AdbExe -s $AdbTarget shell getprop ro.build.version.release 2>$null)
    $bootComplete = (& $AdbExe -s $AdbTarget shell getprop sys.boot_completed 2>$null)
    if ($bootComplete -and ($bootComplete -join "").Trim() -eq "1") { break }
    Start-Sleep -Seconds 1
}
$screenSize = (& $AdbExe -s $AdbTarget shell wm size 2>$null)
$screenDensity = (& $AdbExe -s $AdbTarget shell wm density 2>$null)

if ($androidVer -and $bootComplete -and ($bootComplete -join "").Trim() -eq "1") {
    Report-Check "Android System Boot Completed" $true "Android Version: $androidVer (sys.boot_completed=1)"
    Report-Check "Display Properties Readable" $true "$screenSize | $screenDensity"
} else {
    Report-Check "Android System Boot Completed" $false "Android version or boot_completed could not be queried"
}

# 7. Check Persistent Volume
$volumeCheck = wsl -d Ubuntu -u root -e docker volume ls -f "name=^${VolumeName}$" --format "{{.Name}}" 2>$null
if ($volumeCheck -eq $VolumeName) {
    Report-Check "Persistent Docker Volume Exists" $true "Volume: $VolumeName"
} else {
    Report-Check "Persistent Docker Volume Exists" $false "Volume $VolumeName not found"
}

Write-Host "=================================================================" -ForegroundColor Cyan
if ($allPass) {
    Write-Host " RESULT: ALL HEALTH CHECKS PASSED (100% HEALTHY) " -ForegroundColor Green
} else {
    Write-Host " RESULT: SOME HEALTH CHECKS FAILED              " -ForegroundColor Red
}
Write-Host "=================================================================" -ForegroundColor Cyan
