# YouTube Shorts Automation via Redroid (Android 14)

A dedicated, lightweight, and fully automated pipeline for uploading YouTube Shorts from local video files directly to YouTube channels running in headless or mirrored **Redroid (Remote Android)** Docker containers on Windows 11 / WSL2.

---

## Architecture Overview

```
+-------------------------------------------------------------------------+
|                              Windows Host                               |
|                                                                         |
|   +-----------------------+              +--------------------------+   |
|   |   upload_short.py     |              |     scrcpy.exe           |   |
|   |   (Python Automation) |              |  (Live Screen Mirror)    |   |
|   +-----------+-----------+              +------------+-------------+   |
|               | ADB (127.0.0.1:5801)                  |                 |
+---------------|---------------------------------------|-----------------+
|               |                                       |                 |
|               v                                       v                 |
|   +-----------+---------------------------------------+-------------+   |
|   |                     WSL2 Ubuntu (Docker)                        |   |
|   |                                                                 |   |
|   |   +---------------------------------------------------------+   |   |
|   |   | Container: redroid-01 (Android 14)                      |   |   |
|   |   | - Resolution: 720x1280 @ 320 DPI (30 FPS)               |   |   |
|   |   | - GPU Mode: Guest                                       |   |   |
|   |   | - Volume: redroid-account-01-data (Persistent /data)    |   |   |
|   |   | - App: YouTube (Revanced / MicroG / Official)           |   |   |
|   |   +---------------------------------------------------------+   |   |
|   +-----------------------------------------------------------------+   |
+-------------------------------------------------------------------------+
```

---

## System Requirements & Prerequisites

1. **Windows 11 with WSL2** (Ubuntu distribution installed: `wsl --install -d Ubuntu`).
2. **Docker** installed inside WSL2 Ubuntu (`sudo apt update && sudo apt install -y docker.io`).
3. **Android Platform Tools (ADB)** and **Scrcpy** installed (located at `C:\Users\Shahid\tools\scrcpy` or in your Windows `PATH`).
4. **Python 3.10+** on Windows with required packages:
   ```bash
   pip install uiautomator2 pillow
   ```

---

## Quick Start: Managing the YouTube Redroid Instance

All container lifecycle operations are handled by `redroid.ps1` (or `redroid.sh` inside WSL2).

### 1. Start Container
```powershell
.\redroid.ps1 start 01
```
This automatically ensures WSL2 is running, starts the Docker daemon, launches container `redroid-01` with port `5801` mapped to ADB port `5555`, applies system stability fixes, and verifies ADB connectivity.

### 2. Check Instance Status
```powershell
.\redroid.ps1 status 01
```
Outputs container state, Android version, resolution, DPI, and ADB connection status.

### 3. Open Live Screen Mirror (Scrcpy)
```powershell
.\redroid.ps1 scrcpy 01
# Or double-click: open-android-01.bat
```

### 4. Stop or Restart Container
```powershell
.\redroid.ps1 stop 01
.\redroid.ps1 restart 01
```

---

## Uploading YouTube Shorts

The primary automation script is `upload_short.py`. It pushes the video file to the Android device, triggers the Android MediaScanner, opens the YouTube Create Shorts flow, attaches sound/music if requested, seeks to the exact audio timestamp, sets the title, and publishes the Short.

### Basic Usage
```powershell
# Upload a short with title derived from filename:
python upload_short.py "upload files\my_short.mp4" -u

# Upload and watch the live screen progress via scrcpy:
python upload_short.py "upload files\my_short.mp4" -u -v

# Custom title:
python upload_short.py "upload files\my_short.mp4" -u --title "Epic Moment #shorts"
```

### Adding Sound & Timestamp Seeking
```powershell
# Search for a track and seek to 0:45:
python upload_short.py "upload files\my_short.mp4" -u -s "Sunflower" -t "0:45" -v

# Pick a random 15-second snippet of the track:
python upload_short.py "upload files\my_short.mp4" -u -s "Lo-Fi Beats" -t random -v
```

### Command Flags Reference
| Flag | Description |
|------|-------------|
| `video_path` | Local path to the `.mp4` video file |
| `-u`, `--upload` | Upload flag (or can take the path directly) |
| `-v`, `--view` | Automatically launch `scrcpy` to watch live execution |
| `-a`, `--account` | Redroid account number (default: `01` -> port `5801`) |
| `-T`, `--title` | Custom title for the YouTube Short |
| `-s`, `--sound` | Audio track query to search in YouTube's audio library |
| `-t`, `--timestamp` | Starting timestamp (e.g. `'0:30'`, `'1:15'`, `'45'`, or `'random'`) |
| `--adb` | Path to custom `adb.exe` if not in default location |
| `--scrcpy` | Path to custom `scrcpy.exe` if not in default location |

---

## Visual Inspector & Debugging Tools

- **Web UI Inspector**: Launch `python inspector_web.py` to open a local browser-based inspector displaying live screenshots, element bounding boxes, resource IDs, and XPath selectors.
- **Coordinate Helper**: Run `python get_coords.py` to interactively click and inspect pixel coordinates on screenshots.
- **Step-by-Step Step Debugger**: `python scripts/utils/step_by_step_debug.py` allows manual single-stepping through each phase of the upload workflow.

---

## Directory Structure

```
c:\upload android\
├── open-android-01.bat          # 1-click batch launcher for scrcpy / adb
├── redroid.ps1                  # Primary PowerShell manager for Redroid instances
├── redroid.sh                   # Linux / WSL2 bash instance manager
├── upload_short.py              # Primary YouTube Shorts automation script
├── upload_short_u2.py           # UIAutomator2-based uploader variant
├── inspector_web.py             # Browser-based live Android screen inspector
├── get_coords.py                # Coordinate and bounding box visualizer
├── downloads\                   # Prebuilt YouTube APKs and tools
├── upload files\                # Local video files (.mp4) ready for upload
├── scripts\
│   ├── setup\                   # Environment setup (GApps, MicroG, Binder, tools)
│   └── utils\                   # Audio seek testing, diagnostics, health checks
└── docker_export\               # Exported Instagram Redroid container & migration package
```
