$adb = 'C:\Users\Shahid\tools\scrcpy\adb.exe'

Write-Host "Ensuring container redroid-01 is started..."
wsl -d Ubuntu -u root -e bash -c "systemctl start docker && docker start redroid-01 2>/dev/null || true"

Write-Host "Connecting ADB..."
& $adb connect 127.0.0.1:5801 | Out-Null
Start-Sleep -Seconds 3

# Wait for boot completion
$booted = $false
for ($i = 0; $i -lt 15; $i++) {
    & $adb connect 127.0.0.1:5801 | Out-Null
    $res = (& $adb -s 127.0.0.1:5801 shell getprop sys.boot_completed 2>$null)
    if ($res -and ($res -join "").Trim() -eq '1') {
        $booted = $true
        break
    }
    Start-Sleep -Seconds 2
}

Write-Host "1. Writing persistent data to Android /data/test_account_01.txt..."
& $adb -s 127.0.0.1:5801 shell "echo 'PERSISTENCE_TEST_DATA_VERIFIED_12345' > /data/test_account_01.txt"
$before = ((& $adb -s 127.0.0.1:5801 shell "cat /data/test_account_01.txt") -join "").Trim()
Write-Host "Data before restart: $before"

Write-Host "2. Stopping container redroid-01..."
wsl -d Ubuntu -u root -e docker stop redroid-01
Start-Sleep -Seconds 2

Write-Host "3. Starting container redroid-01..."
wsl -d Ubuntu -u root -e docker start redroid-01

Write-Host "4. Waiting for container and reconnecting ADB..."
Start-Sleep -Seconds 5
for ($i = 0; $i -lt 15; $i++) {
    & $adb connect 127.0.0.1:5801 | Out-Null
    $res = (& $adb -s 127.0.0.1:5801 shell getprop sys.boot_completed 2>$null)
    if ($res -and ($res -join "").Trim() -eq '1') {
        break
    }
    Start-Sleep -Seconds 2
}

Write-Host "5. Reading persistent data after restart..."
$after = ((& $adb -s 127.0.0.1:5801 shell "cat /data/test_account_01.txt") -join "").Trim()
Write-Host "Data after restart: $after"

if ($before -eq $after -and $after -eq 'PERSISTENCE_TEST_DATA_VERIFIED_12345') {
    Write-Host ""
    Write-Host "================================================================"
    Write-Host ">>> SUCCESS: Container data persistence across restarts is 100% verified! <<<"
    Write-Host "================================================================"
} else {
    Write-Host ">>> FAILURE: Data was not persisted <<<"
    exit 1
}
