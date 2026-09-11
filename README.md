# Redroid Android & YouTube Short Automation

Automated YouTube Short uploader and persistent Android emulator management on Windows 11 / WSL2.

---

## 📁 Directory Structure

```
c:\upload android\
├── downloads/                      # Downloaded APKs, videos, images, and temporary files
│   ├── NewPipe.apk
│   └── ...
├── scripts/
│   ├── setup/                      # Setup, installer, and environment provisioning scripts
│   │   ├── docker-wrapper.sh
│   │   ├── extract_mindthegapps.py
│   │   ├── install-tools.ps1
│   │   ├── install_gapps_all.py
│   │   ├── install_microg.py
│   │   ├── install_phonesky.py
│   │   ├── install_yt21.py
│   │   └── setup-binder.sh
│   └── utils/                      # Diagnostics, inspection, and generation utilities
│       ├── check_latest_yt.py
│       ├── check_yt_activities.sh
│       ├── find_gapps.py
│       ├── find_yt_prebuilts.py
│       ├── gen_short.py
│       ├── launch_yt.sh
│       ├── redroid-health.ps1
│       ├── register_video.py
│       ├── test-persistence.ps1
│       └── wait_boot.sh
├── .wslconfig                      # WSL2 kernel & memory configuration
├── open-android-01.bat             # 1-click launcher for Redroid 01 + Scrcpy
├── redroid.ps1                     # PowerShell instance manager (start, stop, scrcpy, health, adb)
├── redroid.sh                      # Bash instance manager for WSL/Linux
├── upload_short.py                 # Main YouTube Short Uploader CLI tool (-u, -v)
└── README.md                       # Project documentation & reference
```

---

## 🚀 Quick Reference

### 1. Upload a YouTube Short
```powershell
# Upload a short and view screen in real-time
python upload_short.py -u "C:\path\to\video.mp4" -v

# Upload with a custom title
python upload_short.py -u "C:\path\to\video.mp4" -t "My Cool Short" -v

# Upload to a specific account instance (e.g. Account 02)
python upload_short.py -u "C:\path\to\video.mp4" -a 02 -v
```

### 2. Manage Android Instances (`redroid.ps1`)
```powershell
# Start instance 01
.\redroid.ps1 start 01

# Open live screen viewer (scrcpy)
.\redroid.ps1 scrcpy 01

# Check instance health & diagnostic checks
.\redroid.ps1 health 01

# Stop instance
.\redroid.ps1 stop 01
```
