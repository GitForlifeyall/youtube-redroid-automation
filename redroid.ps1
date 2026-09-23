<#
.SYNOPSIS
    Redroid Android Instance Manager on Windows 11 / WSL2
.DESCRIPTION
    Manages persistent Redroid Android containers (Start, Stop, Restart, Status, Scrcpy, ADB).
.EXAMPLE
    .\redroid.ps1 start 01
    .\redroid.ps1 stop 01
    .\redroid.ps1 restart 01
    .\redroid.ps1 status 01
    .\redroid.ps1 scrcpy 01
    .\redroid.ps1 adb 01 shell getprop ro.build.version.release
#>

param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "status", "scrcpy", "adb", "health", "help")]
    [string]$Action,

    [Parameter(Position=1, Mandatory=$false)]
    [string]$Account = "01",

    [Parameter(Position=2, ValueFromRemainingArguments=$true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Continue"
if (Test-Path Variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

# Paths
$ToolsDir = "C:\Users\Shahid\tools\scrcpy"
$AdbExe = Join-Path $ToolsDir "adb.exe"
$ScrcpyExe = Join-Path $ToolsDir "scrcpy.exe"

# If local tools don't exist, check PATH
if (-not (Test-Path $AdbExe)) {
    $foundAdb = Get-Command adb -ErrorAction SilentlyContinue
    if ($foundAdb) { $AdbExe = $foundAdb.Source }
}
if (-not (Test-Path $ScrcpyExe)) {
    $foundScrcpy = Get-Command scrcpy -ErrorAction SilentlyContinue
    if ($foundScrcpy) { $ScrcpyExe = $foundScrcpy.Source }
}

# Container and Port mapping (Account 01 -> 5801, Account 02 -> 5802, etc.)
$AccountNum = [int]$Account
$HostPort = 5800 + $AccountNum
$ContainerName = "redroid-$Account"
$VolumeName = "redroid-account-$Account-data"
$AdbTarget = "127.0.0.1:$HostPort"

function Ensure-WslAndDocker {
    # Keep WSL2 VM alive in the background on Windows
    $wslKeeper = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*wsl*" -and $_.CommandLine -like "*Ubuntu*" -and $_.CommandLine -like "*sleep*" }
    if (-not $wslKeeper) {
        Start-Process -FilePath "wsl.exe" -ArgumentList "-d", "Ubuntu", "-u", "root", "--exec", "/bin/sleep", "infinity" -WindowStyle Hidden
        Start-Sleep -Milliseconds 500
    }

    # Check if WSL is responsive
    $wslCheck = ((wsl -d Ubuntu -u root -e bash -c "echo WSL_OK" 2>$null) -join "").Trim()
    if ($wslCheck -ne "WSL_OK") {
        Write-Host "[*] Starting WSL2 Ubuntu..." -ForegroundColor Cyan
        wsl -d Ubuntu -u root -e true | Out-Null
    }

    # Ensure systemd linger and Docker service
    wsl -d Ubuntu -u root -e bash -c "loginctl enable-linger root 2>/dev/null; systemctl is-active docker >/dev/null || systemctl start docker" | Out-Null
}

function Connect-Adb {
    param([int]$MaxAttempts = 15)
    Write-Host "[*] Connecting ADB to $AdbTarget..." -ForegroundColor Cyan
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        & $AdbExe connect $AdbTarget | Out-Null
        $devices = (& $AdbExe devices) -join "`n"
        if ($devices -match [regex]::Escape($AdbTarget) + "\s+device") {
            $res = (& $AdbExe -s $AdbTarget shell getprop sys.boot_completed 2>$null)
            if ($res -and ($res -join "").Trim() -eq "1") {
                Write-Host "[+] Android boot completed and ADB is online!" -ForegroundColor Green
                return $true
            }
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "[!] ADB connected, but Android is still initializing..." -ForegroundColor Yellow
    return $false
}

switch ($Action.ToLower()) {
    "start" {
        Write-Host "======================================================" -ForegroundColor Cyan
        Write-Host "  STARTING REDROID ACCOUNT $Account" -ForegroundColor Cyan
        Write-Host "======================================================" -ForegroundColor Cyan

        Ensure-WslAndDocker

        # Check if container exists
        $containerExists = wsl -d Ubuntu -u root -e docker ps -a -q -f "name=^/${ContainerName}$"
        if ([string]::IsNullOrWhiteSpace($containerExists)) {
            Write-Host "[*] Creating persistent volume: $VolumeName" -ForegroundColor Cyan
            wsl -d Ubuntu -u root -e docker volume create $VolumeName | Out-Null

            Write-Host "[*] Creating and starting container: $ContainerName on port $HostPort..." -ForegroundColor Cyan
            wsl -d Ubuntu -u root -e docker run -d `
                --name $ContainerName `
                --restart always `
                --privileged `
                -v "${VolumeName}:/data" `
                -p "${HostPort}:5555" `
                redroid-fixed:14.0 `
                androidboot.redroid_width=720 `
                androidboot.redroid_height=1280 `
                androidboot.redroid_dpi=320 `
                androidboot.redroid_fps=30 `
                androidboot.redroid_gpu_mode=guest `
                androidboot.use_memfd=1 `
                androidboot.selinux=permissive `
                ro.product.brand=google `
                ro.product.model="Pixel 8 Pro" `
                ro.product.name=husky `
                ro.product.device=husky `
                ro.product.manufacturer=Google `
                ro.build.fingerprint=google/husky/husky:14/UD1A.230803.041/10808477:user/release-keys `
                ro.build.type=user `
                ro.build.tags=release-keys | Out-Null
        } else {
            Write-Host "[*] Starting existing container: $ContainerName..." -ForegroundColor Cyan
            wsl -d Ubuntu -u root -e docker start $ContainerName | Out-Null
        }

        Connect-Adb -MaxAttempts 30 | Out-Null

        # Disable crashing mock bluetooth HAL in guest container
        wsl -d Ubuntu -u root -e bash -c "docker exec $ContainerName stop vendor.bluetooth-1-1 2>/dev/null; docker exec $ContainerName pm disable com.android.bluetooth 2>/dev/null" | Out-Null

        # Keep screen awake and prevent timeout
        & $AdbExe -s $AdbTarget shell settings put system screen_off_timeout 2147483647 2>$null | Out-Null
        & $AdbExe -s $AdbTarget shell settings put global stay_on_while_plugged_in 3 2>$null | Out-Null

        Write-Host ""
        Write-Host "[+] Redroid Account $Account is ACTIVE!" -ForegroundColor Green
        Write-Host "    - Container:  $ContainerName"
        Write-Host "    - Volume:     $VolumeName (Persistent)"
        Write-Host "    - ADB Target: $AdbTarget"
        Write-Host "    - Resolution: 720x1280 @ 320 dpi (30 fps)"
    }

    "stop" {
        Write-Host "======================================================" -ForegroundColor Yellow
        Write-Host "  STOPPING REDROID ACCOUNT $Account" -ForegroundColor Yellow
        Write-Host "======================================================" -ForegroundColor Yellow

        & $AdbExe disconnect $AdbTarget 2>$null | Out-Null
        Write-Host "[*] Stopping container: $ContainerName..." -ForegroundColor Yellow
        wsl -d Ubuntu -u root -e docker stop $ContainerName 2>$null | Out-Null
        Write-Host "[+] Redroid Account $Account STOPPED." -ForegroundColor Green
    }

    "restart" {
        & $MyInvocation.MyCommand.Path "stop" $Account
        Start-Sleep -Seconds 2
        & $MyInvocation.MyCommand.Path "start" $Account
    }

    "status" {
        Write-Host "======================================================" -ForegroundColor Cyan
        Write-Host "  STATUS FOR REDROID ACCOUNT $Account" -ForegroundColor Cyan
        Write-Host "======================================================" -ForegroundColor Cyan

        Ensure-WslAndDocker

        $containerInfo = (wsl -d Ubuntu -u root -e docker ps -a -f "name=^/${ContainerName}$" --format "{{.Status}}" 2>$null) -join ""
        if ([string]::IsNullOrWhiteSpace($containerInfo)) {
            Write-Host "Container State: NOT CREATED" -ForegroundColor DarkGray
            return
        }

        Write-Host "Container State: $containerInfo"
        if ($containerInfo -like "*Up*") {
            & $AdbExe connect $AdbTarget 2>$null | Out-Null
            $androidVer = ((& $AdbExe -s $AdbTarget shell getprop ro.build.version.release 2>$null) -join "").Trim()
            $screenSize = ((& $AdbExe -s $AdbTarget shell wm size 2>$null) -join " ").Trim()
            $screenDensity = ((& $AdbExe -s $AdbTarget shell wm density 2>$null) -join " ").Trim()
            $bootComplete = ((& $AdbExe -s $AdbTarget shell getprop sys.boot_completed 2>$null) -join "").Trim()

            Write-Host "Android Version: $androidVer"
            Write-Host "Boot Completed:  $bootComplete"
            Write-Host "Display Size:    $screenSize"
            Write-Host "Display Density: $screenDensity"
            Write-Host "ADB Connection:  $AdbTarget (ONLINE)" -ForegroundColor Green
        } else {
            Write-Host "ADB Connection:  OFFLINE" -ForegroundColor Yellow
        }
    }

    "scrcpy" {
        Ensure-WslAndDocker
        $isRunning = (wsl -d Ubuntu -u root -e docker inspect -f "{{.State.Running}}" $ContainerName 2>$null).Trim()
        if ($isRunning -ne "true") {
            Write-Host "[*] Container $ContainerName is not running. Starting it now..." -ForegroundColor Cyan
            & $MyInvocation.MyCommand.Path "start" $Account
        }
        Connect-Adb -MaxAttempts 20 | Out-Null
        Write-Host "[*] Launching scrcpy visual interface for Account $Account..." -ForegroundColor Green
        & $ScrcpyExe -s $AdbTarget --video-codec=h264 --video-bit-rate=4M --max-fps=30 --no-audio --stay-awake --window-title "Redroid Account $Account ($AdbTarget)"
    }

    "adb" {
        if (-not $ExtraArgs) {
            Write-Host "Usage: .\redroid.ps1 adb $Account <command>" -ForegroundColor Yellow
            return
        }
        Ensure-WslAndDocker
        & $AdbExe connect $AdbTarget 2>$null | Out-Null
        $cmdLine = $ExtraArgs -join " "
        cmd /c "`"$AdbExe`" -s $AdbTarget $cmdLine"
    }

    "health" {
        $healthScript = Join-Path $PSScriptRoot "scripts\utils\redroid-health.ps1"
        if (-not (Test-Path $healthScript)) {
            $healthScript = Join-Path $PSScriptRoot "redroid-health.ps1"
        }
        & $healthScript $Account
    }

    "help" {
        Get-Help $MyInvocation.MyCommand.Path -Detailed
    }
}
