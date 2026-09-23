<#
.SYNOPSIS
    Instagram Redroid 1-Click Importer & Launcher for Windows 10/11 (WSL2)
.DESCRIPTION
    Loads the exported Docker image and restores the /data volume inside WSL2 Ubuntu,
    then starts the persistent Instagram Redroid container.
#>

$ErrorActionPreference = "Stop"

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Instagram Redroid 1-Click Importer & Launcher" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Ensure WSL Ubuntu is installed
$wslCheck = wsl -l -q 2>$null
if (-not ($wslCheck -match "Ubuntu")) {
    Write-Host "[!] Ubuntu distribution not found in WSL." -ForegroundColor Red
    Write-Host "    Please run: wsl --install -d Ubuntu" -ForegroundColor Yellow
    exit 1
}

# 2. Check WSL path to this folder
$scriptDirWin = $PSScriptRoot
$driveLetter = $scriptDirWin.Substring(0, 1).ToLower()
$pathWithoutDrive = $scriptDirWin.Substring(2).Replace("\", "/")
$wslDir = "/mnt/$driveLetter$pathWithoutDrive"

Write-Host "[*] Executing import inside WSL2 Ubuntu..." -ForegroundColor Cyan
wsl -d Ubuntu -u root -e bash -c "chmod +x '$wslDir/import_and_run.sh' && '$wslDir/import_and_run.sh'"

# 3. Connect ADB from Windows
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if ($adbCmd) {
    Write-Host "[*] Connecting local Windows ADB to 127.0.0.1:5801..." -ForegroundColor Cyan
    & $adbCmd.Source connect 127.0.0.1:5801 | Out-Null
    Write-Host "[+] ADB connected!" -ForegroundColor Green
} else {
    Write-Host "[*] ADB not found in Windows PATH. Connect via: adb connect 127.0.0.1:5801" -ForegroundColor Yellow
}

$scrcpyCmd = Get-Command scrcpy -ErrorAction SilentlyContinue
if ($scrcpyCmd) {
    Write-Host "[+] To view screen, run: scrcpy -s 127.0.0.1:5801" -ForegroundColor Green
}
