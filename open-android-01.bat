@echo off
title Launching Redroid Account 01
cd /d "c:\upload android"
echo Starting Redroid Android 01 instance...
powershell -ExecutionPolicy Bypass -File .\redroid.ps1 start 01
echo Launching Scrcpy display window...
start "" "C:\Users\Shahid\tools\scrcpy\scrcpy.exe" -s 127.0.0.1:5801 --video-codec=h264 --video-bit-rate=4M --max-fps=30 --no-audio --stay-awake --window-title "Redroid Account 01"
