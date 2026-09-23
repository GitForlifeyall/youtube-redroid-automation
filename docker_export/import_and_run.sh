#!/usr/bin/env bash
set -e

# ==============================================================================
# Instagram Redroid 1-Click Importer & Launcher
# ==============================================================================
# Usage:
#   sudo ./import_and_run.sh
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_ARCHIVE="$SCRIPT_DIR/redroid-instagram-image.tar.gz"
DATA_ARCHIVE="$SCRIPT_DIR/redroid-insta-data.tar.gz"
CONTAINER_NAME="redroid-01"
VOLUME_NAME="redroid-account-01-data"
HOST_PORT="5801"

echo "======================================================"
echo "  Instagram Redroid 1-Click Importer & Launcher"
echo "======================================================"

# 1. Check Docker
if ! command -v docker &> /dev/null; then
    echo "[!] Docker is not installed or not in PATH."
    echo "    Please install Docker first (e.g. 'sudo apt update && sudo apt install -y docker.io')."
    exit 1
fi

systemctl is-active docker >/dev/null 2>&1 || systemctl start docker

# 2. Check and load binder modules if available
if [ ! -e /dev/binder ] || [ ! -e /dev/ashmem ]; then
    echo "[*] Checking binder/ashmem kernel modules..."
    modprobe binder_linux devices="binder,hwbinder,vndbinder" 2>/dev/null || true
    modprobe ashmem_linux 2>/dev/null || true
    if [ -f "$SCRIPT_DIR/setup-binder.sh" ] && ([ ! -e /dev/binder ]); then
        echo "[*] Running binder setup helper..."
        bash "$SCRIPT_DIR/setup-binder.sh" || true
    fi
fi

# 3. Load Docker Image
if [ -f "$IMAGE_ARCHIVE" ]; then
    echo "[*] Importing Docker image from $IMAGE_ARCHIVE..."
    docker load -i "$IMAGE_ARCHIVE"
    docker tag redroid-instagram:latest redroid-fixed:14.0 2>/dev/null || true
else
    echo "[!] Image archive not found at: $IMAGE_ARCHIVE"
    exit 1
fi

# 4. Stop existing container if running
if [ "$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "[*] Removing existing container: $CONTAINER_NAME..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

# 5. Restore Persistent Data Volume
echo "[*] Creating Docker volume: $VOLUME_NAME..."
docker volume create "$VOLUME_NAME" >/dev/null 2>&1 || true

if [ -f "$DATA_ARCHIVE" ]; then
    VOLUME_DIR="/var/lib/docker/volumes/$VOLUME_NAME/_data"
    echo "[*] Restoring Android data volume into $VOLUME_DIR..."
    mkdir -p "$VOLUME_DIR"
    tar -xzf "$DATA_ARCHIVE" -C "$VOLUME_DIR"
    echo "[+] Persistent data successfully restored!"
else
    echo "[!] Data archive not found at: $DATA_ARCHIVE. Container will boot with fresh /data."
fi

# 6. Launch Container
echo "[*] Launching $CONTAINER_NAME on port $HOST_PORT..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart always \
    --privileged \
    -v "${VOLUME_NAME}:/data" \
    -p "${HOST_PORT}:5555" \
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

echo "[*] Waiting for Android boot to finish..."
sleep 6

# Post-start fix for Bluetooth crashing service
docker exec "$CONTAINER_NAME" stop vendor.bluetooth-1-1 2>/dev/null || true
docker exec "$CONTAINER_NAME" pm disable com.android.bluetooth 2>/dev/null || true

echo ""
echo "======================================================"
echo "[+] Instagram Redroid is ACTIVE!"
echo "    - Container:  $CONTAINER_NAME"
echo "    - Port:       $HOST_PORT (ADB target: 127.0.0.1:$HOST_PORT)"
echo "    - Connect:    adb connect 127.0.0.1:$HOST_PORT"
echo "    - Screen:     scrcpy -s 127.0.0.1:$HOST_PORT"
echo "======================================================"
