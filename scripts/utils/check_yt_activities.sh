export DOCKER_HOST=unix:///var/run/docker.sock

# Let's check YouTube version name / code and what activities are exported in com.google.android.youtube
docker exec redroid-01 dumpsys package com.google.android.youtube | grep -A 20 "Activity" | head -n 30
