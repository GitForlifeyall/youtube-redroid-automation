# AI Coding Agent Setup & Operation Guide

> **Target Audience**: Autonomous AI Coding Agents (Antigravity, Claude Code, Devin, Cursor Agent, etc.) and Developers.
> **Repository Purpose**: Automated YouTube Shorts and Instagram Reels video publishing pipelines utilizing containerized Android (Redroid) running on WSL2 / Linux.

---

## 1. System Architecture Overview

This project bypasses emulator bloat (such as BlueStacks or LDPlayer) by using **Redroid (Remote Android)**:
- **Guest OS**: Android 14 (AOSP) running in a lightweight Docker container.
- **Display & Input**: Rendered via software guest mode (`androidboot.redroid_gpu_mode=guest`) and mirrored via `scrcpy`.
- **Control Interface**: Native Android Debug Bridge (ADB) on port `5801` (`127.0.0.1:5801` mapped to container port `5555`).
- **Automation Engine**: Python automation scripts (`upload_short.py` for YouTube Shorts, `upload_reel.py` for Instagram Reels) utilizing direct ADB intents, UIAutomator node hierarchy parsing, and precise audio scrubber calibration.

---

## 2. Docker Container & Volume Copy Links (For Agent Access)

The complete preconfigured Docker container image and persistent Android volume (containing installed Instagram apps, YouTube apps, Google Play services, and user logins) are backed up locally.

### Local Storage Locations on Origin Machine:
- **Windows Junction**: `C:\upload android\docker_export\`
- **Physical Drive D: Path**: `D:\redroid_export\`
- **WSL2 Ubuntu Path**: `/mnt/d/redroid_export/`

### File Manifest:
| Filename | Size | Description |
|----------|------|-------------|
| `redroid-instagram-image.tar.gz` | **~854 MB** | Docker image archive (`redroid-instagram:latest`) with stability patches and build properties. |
| `redroid-insta-data.tar.gz` | **~2.76 GB** | Compressed `/data` volume containing installed applications, logins, and configurations. |
| `import_and_run.ps1` | **1.8 KB** | 1-Click PowerShell deployment script for Windows 10/11 with WSL2. |
| `import_and_run.sh` | **4.1 KB** | 1-Click Bash deployment script for Linux or native WSL2. |
| `upload_reel.py` | **15.7 KB** | Standalone Instagram Reel upload script ready for execution on the target machine. |
| `setup-binder.sh` | **748 B** | Helper script to verify and initialize Android `binder_linux` kernel IPC modules. |
| `build_stub_and_patch.py` | **4.4 KB** | Native ARM64 crash-bypass stub builder (used if patching clean Instagram APKs). |

### Transfer Methods for the Coding Agent:
When setting up on another system, transfer the contents of `docker_export/`:
1. **Network Transfer (LAN)**:
   ```bash
   scp -r user@ORIGIN_IP:/mnt/d/redroid_export /destination/path/docker_export
   ```
2. **Local Drive / USB**: Copy the folder directly from `D:\redroid_export` or `c:\upload android\docker_export` to external media.
3. **Cloud Storage**: If using cloud storage (Google Drive / OneDrive / S3), compress into a single archive or sync the directory using `rclone`.

---

## 3. Autonomous Setup Instructions for the AI Agent

When an AI agent initializes this repository on any host, execute the following steps in sequence:

### Step 3.1: Verify Host Prerequisites
```bash
# Verify WSL2 status (Windows only)
wsl -l -v

# Verify Docker daemon is running inside WSL2 Ubuntu
wsl -d Ubuntu -u root -e systemctl is-active docker
```
If Docker is not running:
```bash
wsl -d Ubuntu -u root -e systemctl start docker
```

### Step 3.2: Verify Host Python Environment
Install required Python packages:
```bash
pip install uiautomator2 pillow
```

### Step 3.3: Verify ADB & Scrcpy
Check if `adb` and `scrcpy` are available in PATH:
```powershell
Get-Command adb, scrcpy -ErrorAction SilentlyContinue
```
*(Default fallback path configured in scripts: `C:\Users\Shahid\tools\scrcpy\` or system PATH).*

---

## 4. Running the YouTube Redroid Pipeline

### Step 4.1: Start the Redroid Instance
Run the PowerShell manager from the repository root:
```powershell
.\redroid.ps1 start 01
```
*Expected output*: Confirms container `redroid-01` is running on port `5801` and ADB connection `127.0.0.1:5801` is online with `sys.boot_completed=1`.

### Step 4.2: Health Check
```powershell
.\redroid.ps1 status 01
```

### Step 4.3: Execute YouTube Shorts Upload
To upload a video file:
```powershell
python upload_short.py "upload files\your_video.mp4" -u --title "My Automated Short #shorts"
```

To upload with YouTube audio library track and exact timestamp seeking:
```powershell
python upload_short.py "upload files\your_video.mp4" -u -s "Track Title" -t "0:45" -v
```

### Step 4.4: Live Monitoring
To mirror the screen while uploading, use `-v` or:
```powershell
.\redroid.ps1 scrcpy 01
```

---

## 5. Setting up Instagram Redroid on the Other Machine

When the agent or user wants to set up Instagram on the second system:

1. Navigate to the copied `docker_export/` directory.
2. Run the 1-click installer:
   - **Windows**: `powershell -ExecutionPolicy Bypass -File .\import_and_run.ps1`
   - **Linux / WSL2**: `sudo bash ./import_and_run.sh`
3. Verify ADB connection:
   ```bash
   adb connect 127.0.0.1:5801
   adb -s 127.0.0.1:5801 devices
   ```
4. Run Reel Upload:
   ```bash
   python upload_reel.py -u "video.mp4" -c "My Instagram Reel #reels" -v
   ```

---

## 6. Troubleshooting & Diagnostics Reference for Agents

| Issue | Root Cause | Agent Remediation |
|-------|------------|-------------------|
| `failed to connect to 127.0.0.1:5801` | Container not running or Docker service stopped | Run `wsl -d Ubuntu -u root -e systemctl start docker` followed by `.\redroid.ps1 restart 01`. |
| `sys.boot_completed != 1` | Android container still initializing | Wait 10-15 seconds and test `adb -s 127.0.0.1:5801 shell getprop sys.boot_completed`. |
| YouTube video not appearing in gallery | Android MediaStore indexing delay | Execute `adb -s 127.0.0.1:5801 shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file:///storage/emulated/0/Movies/<filename>"`. |
| Scrcpy window fails to open | Scrcpy already active or port busy | Kill existing instances using `taskkill /F /IM scrcpy.exe` and re-run. |
| Disk space exhaustion | Docker layer/volume buildup | Monitor `Get-PSDrive C` and run `docker system prune -f` in WSL2 if necessary. |
