export DOCKER_HOST=unix:///var/run/docker.sock

docker exec redroid-01 pm grant com.google.android.youtube android.permission.CAMERA
docker exec redroid-01 pm grant com.google.android.youtube android.permission.RECORD_AUDIO
docker exec redroid-01 pm grant com.google.android.youtube android.permission.READ_MEDIA_VIDEO
docker exec redroid-01 pm grant com.google.android.youtube android.permission.READ_MEDIA_IMAGES
docker exec redroid-01 pm grant com.google.android.youtube android.permission.POST_NOTIFICATIONS

docker exec redroid-01 am force-stop com.google.android.youtube
docker exec redroid-01 am start -n com.google.android.youtube/com.google.android.apps.youtube.app.WatchWhileActivity

sleep 5

docker exec redroid-01 uiautomator dump /data/local/tmp/ui.xml
docker exec redroid-01 cat /data/local/tmp/ui.xml
