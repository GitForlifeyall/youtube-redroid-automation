# Instagram Redroid Portable Export Package

This package contains everything needed to run your configured **Instagram Redroid (Android 14)** instance on any other machine.

## Contents
- `redroid-instagram-image.tar.gz`: The committed Docker container image (~815 MB).
- `redroid-insta-data.tar.gz`: The persistent Android `/data` volume with Instagram apps, logins, and configurations (~2.6 GB).
- `import_and_run.ps1`: Windows PowerShell 1-click installer and launcher.
- `import_and_run.sh`: Linux / WSL2 1-click installer and launcher.
- `upload_reel.py`: Standalone Instagram Reel uploader.
- `setup-binder.sh`: Binder kernel module setup helper.
- `build_stub_and_patch.py`: ARM64 stub compiler for patching fresh Instagram APKs if needed.

## 1-Click Startup

### On Windows 10/11 (with WSL2 Ubuntu & Docker):
```powershell
powershell -ExecutionPolicy Bypass -File .\import_and_run.ps1
```

### On Linux or inside WSL2 directly:
```bash
sudo bash import_and_run.sh
```

## Connecting After Start
- **ADB**: `adb connect 127.0.0.1:5801`
- **Scrcpy**: `scrcpy -s 127.0.0.1:5801`
- **Upload Reel**: `python upload_reel.py -u "video.mp4" -c "My Reel" -v`

For the full detailed setup guide, refer to `INSTA_REDROID_SETUP.md` in the main repository.
