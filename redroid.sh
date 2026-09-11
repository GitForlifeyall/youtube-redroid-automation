#!/usr/bin/env bash
set -e

ACTION="${1:-help}"
ACCOUNT="${2:-01}"
HOST_PORT=$((5800 + 10#$ACCOUNT))
CONTAINER_NAME="redroid-$ACCOUNT"
VOLUME_NAME="redroid-account-$ACCOUNT-data"

case "$ACTION" in
    start)
        echo "Starting Redroid Account $ACCOUNT..."
        docker volume create "$VOLUME_NAME" >/dev/null 2>&1 || true
        if [ ! "$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)" ]; then
            docker run -d \
                --name "$CONTAINER_NAME" \
                --privileged \
                -v "${VOLUME_NAME}:/data" \
                -p "${HOST_PORT}:5555" \
                redroid-fixed:14.0 \
                androidboot.redroid_width=720 \
                androidboot.redroid_height=1280 \
                androidboot.redroid_dpi=320 \
                androidboot.redroid_fps=30 \
                androidboot.redroid_gpu_mode=guest \
                androidboot.use_memfd=1 \
                androidboot.selinux=permissive
        else
            docker start "$CONTAINER_NAME"
        fi
        echo "Redroid Account $ACCOUNT started on port $HOST_PORT."
        ;;
    stop)
        echo "Stopping Redroid Account $ACCOUNT..."
        docker stop "$CONTAINER_NAME" || true
        echo "Redroid Account $ACCOUNT stopped."
        ;;
    restart)
        "$0" stop "$ACCOUNT"
        sleep 2
        "$0" start "$ACCOUNT"
        ;;
    status)
        echo "Status of $CONTAINER_NAME:"
        docker ps -a -f "name=^/${CONTAINER_NAME}$"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status} [account_id (e.g. 01)]"
        exit 1
        ;;
esac
