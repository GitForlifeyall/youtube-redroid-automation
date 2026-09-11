$toolsDir = 'C:\Users\Shahid\tools'
if (-not (Test-Path $toolsDir)) {
    New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
}
$zipPath = Join-Path $toolsDir 'scrcpy.zip'
$scrcpyDir = Join-Path $toolsDir 'scrcpy'

Write-Host "Downloading scrcpy & adb..."
Invoke-WebRequest -Uri 'https://github.com/Genymobile/scrcpy/releases/download/v3.1/scrcpy-win64-v3.1.zip' -OutFile $zipPath

Write-Host "Extracting..."
Expand-Archive -Path $zipPath -DestinationPath $toolsDir -Force
Remove-Item -Path $zipPath -Force

$extracted = Get-ChildItem -Path $toolsDir -Directory -Filter 'scrcpy-win64*' | Select-Object -First 1
if ($extracted -and ($extracted.FullName -ne $scrcpyDir)) {
    if (Test-Path $scrcpyDir) { Remove-Item -Recurse -Force $scrcpyDir }
    Rename-Item -Path $extracted.FullName -NewName 'scrcpy'
}

# Add tools and scrcpy to User PATH if not present
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notlike "*$scrcpyDir*") {
    [Environment]::SetEnvironmentVariable('Path', "$scrcpyDir;$userPath", 'User')
    $env:Path = "$scrcpyDir;$env:Path"
}

Write-Host "Verifying binaries:"
Get-ChildItem $scrcpyDir
& "$scrcpyDir\adb.exe" version
& "$scrcpyDir\scrcpy.exe" --version
