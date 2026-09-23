# Instagram Redroid Migration & Secondary System Setup Guide

This guide details how to take the exported Instagram Redroid container and data volume from this repository and set up a fully functional, persistent **Instagram Redroid instance** on your second machine.

---

## 1. Export Files Overview

All necessary files are located in:
`c:\upload android\docker_export\` (mapped directly to `D:\redroid_export\`).

Copy the entire `docker_export\` folder to an external drive, network share, or USB stick to transfer to your other PC:

| File | Purpose | Size |
|------|---------|------|
| `redroid-instagram-image.tar.gz` | Committed Docker Image (`redroid-instagram:latest`) with system configurations | ~815 MB |
| `redroid-insta-data.tar.gz` | Persistent `/data` volume containing installed Instagram apps, logins, and settings | ~2.6 GB |
| `import_and_run.ps1` | Windows 1-click automated import & launch script | 2 KB |
| `import_and_run.sh` | Linux / WSL2 bash automated import & launch script | 4 KB |
| `upload_reel.py` | Standalone Instagram Reel automation script | 16 KB |
| `setup-binder.sh` | Binder IPC kernel module initialization helper | 1 KB |
| `build_stub_and_patch.py` | Native ARM64 crash-bypass builder if reinstalling clean Instagram | 4 KB |

---

## 2. Prerequisites on the Other System

### On Windows 10/11:
1. **Enable WSL2 and Install Ubuntu**:
   Open an Administrator PowerShell:
   ```powershell
   wsl --install -d Ubuntu
   ```
   Restart the PC if prompted, then create your Ubuntu user.

2. **Install Docker in WSL2 Ubuntu**:
   Inside Ubuntu (`wsl -d Ubuntu`):
   ```bash
   sudo apt update
   sudo apt install -y docker.io
   sudo usermod -aG docker $USER
   sudo systemctl enable --now docker
   ```

3. **Install Tools (ADB & Scrcpy)**:
   - Download [scrcpy](https://github.com/Genymobile/scrcpy/releases) and extract it (e.g., to `C:\tools\scrcpy`).
   - Add `C:\tools\scrcpy` to your Windows System `PATH` so `adb` and `scrcpy` are available from any command prompt.

### On Ubuntu / Linux:
1. Docker installed: `sudo apt install docker.io`.
2. ADB and Scrcpy installed: `sudo apt install adb scrcpy`.
3. Binder kernel module (standard in Linux 5.15+ / 6.x kernels, or loaded via `setup-binder.sh`).

---

## 3. Method A: 1-Click Automated Import (Recommended)

### On Windows:
1. Copy the `docker_export` folder to your desired location (e.g. `C:\docker_export` or `D:\docker_export`).
2. Open PowerShell in that folder and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\import_and_run.ps1
   ```
3. The script will:
   - Load `redroid-instagram-image.tar.gz` into Docker.
   - Create and extract `redroid-insta-data.tar.gz` into `/var/lib/docker/volumes/redroid-account-01-data/_data`.
   - Start the container `redroid-01` with port `5801` mapped to ADB port `5555`.
   - Connect Windows ADB to `127.0.0.1:5801`.

### On Linux / WSL2 directly:
```bash
cd /path/to/docker_export
sudo bash import_and_run.sh
```

---

## 4. Method B: Manual Step-by-Step Installation

If you prefer running the commands manually:

### Step 1: Load the Docker Image
```bash
docker load -i redroid-instagram-image.tar.gz
```

### Step 2: Create and Restore the Data Volume
```bash
# Create volume
docker volume create redroid-account-01-data

# Restore persistent apps and data
sudo tar -xzf redroid-insta-data.tar.gz -C /var/lib/docker/volumes/redroid-account-01-data/_data
```

### Step 3: Run the Redroid Container
Launch the container using the exact verified hardware and Android parameters:
```bash
docker run -d \
    --name redroid-01 \
    --restart always \
    --privileged \
    -v "redroid-account-01-data:/data" \
    -p "5801:5555" \
    redroid-instagram:latest \
    androidboot.redroid_width=720 \
    androidboot.redroid_height=1280 \
    androidboot.redroid_dpi=320 \
    androidboot.redroid_fps=30 \
    androidboot.redroid_gpu_mode=guest \
    androidboot.use_memfd=1 \
    androidboot.selinux=permissive \
    ro.product.brand=google \
    ro.product.model="Pixel 8 Pro" \
    ro.product.name=husky \
    ro.product.device=husky \
    ro.product.manufacturer=Google \
    ro.build.fingerprint=google/husky/husky:14/UD1A.230803.041/10808477:user/release-keys \
    ro.build.type=user \
    ro.build.tags=release-keys
```

### Step 4: Disable Crashing Bluetooth Subsystem
Redroid containers don't have physical Bluetooth hardware; stopping this prevents background log spam:
```bash
docker exec redroid-01 stop vendor.bluetooth-1-1 2>/dev/null || true
docker exec redroid-01 pm disable com.android.bluetooth 2>/dev/null || true
```

---

## 5. Connecting and Verifying Instagram

### Connect ADB
```powershell
adb connect 127.0.0.1:5801
adb -s 127.0.0.1:5801 devices
```

### Launch Scrcpy (Live Display)
```powershell
scrcpy -s 127.0.0.1:5801 --window-title "Instagram Redroid (127.0.0.1:5801)"
```

### Verify Installed Instagram Packages
Inside the container, run:
```powershell
adb -s 127.0.0.1:5801 shell pm list packages | findstr "insta"
```
You will see `com.instagram.android`, `com.instagram.lite`, or `com.instander.android` already installed with all your data intact.

### Launch Instagram Manually
```powershell
adb -s 127.0.0.1:5801 shell am start -n com.instagram.android/com.instagram.android.activity.MainTabActivity
```

---

## 6. Running Reel Upload Automation on the Other System

The standalone upload script is provided inside the `docker_export/` folder as `upload_reel.py`.

```powershell
# Basic upload
python upload_reel.py -u "my_video.mp4" -c "My Awesome Reel #reels" -v

# Upload with sound selection & timestamp
python upload_reel.py -u "my_video.mp4" -s "Sunflower" -t "1:30" -c "Great Song" -v

# Dry run (walks through upload sequence up to final share)
python upload_reel.py -u "my_video.mp4" --dry-run -v
```

---

## 7. Troubleshooting

- **WSL Binder Issues**: If Android fails to boot, run `sudo bash setup-binder.sh` to compile/load the `binder_linux` kernel module.
- **Port Conflict**: If port `5801` is already in use, change `-p "5801:5555"` to another port (e.g. `5802:5555`) in `import_and_run.sh` / `docker run` command, and connect via `adb connect 127.0.0.1:5802`.
- **Display Glitches**: Ensure `androidboot.redroid_gpu_mode=guest` is set. Guest software rendering ensures maximum compatibility across all virtual machines and WSL2 instances.
