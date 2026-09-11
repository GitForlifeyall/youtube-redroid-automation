export DOCKER_HOST=unix:///var/run/docker.sock
while true; do
    STATUS=$(docker exec redroid-01 getprop sys.boot_completed 2>&1 | tr -d '\r\n')
    if [ "$STATUS" = "1" ]; then
        echo "Boot completed!"
        break
    fi
    echo "Current status: $STATUS"
    sleep 2
done
docker exec redroid-01 pm list packages | grep -E "google|vending"
