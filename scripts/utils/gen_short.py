import subprocess, os

# Install ffmpeg in WSL if not present
subprocess.run(['apt-get', 'update', '-qq'])
subprocess.run(['apt-get', 'install', '-y', '-qq', 'ffmpeg'])

# Generate vertical short video (720x1280, 5 seconds, H.264 baseline + AAC audio)
out_mp4 = '/tmp/sample_short_h264.mp4'
cmd = [
    'ffmpeg', '-y',
    '-f', 'lavfi', '-i', 'testsrc=duration=5:size=720x1280:rate=30',
    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-profile:v', 'baseline', '-level', '3.0',
    '-c:a', 'aac', '-b:a', '128k',
    '-shortest',
    out_mp4
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("FFmpeg result:", res.returncode)

# Copy to redroid container
os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
subprocess.run(['docker', 'cp', out_mp4, 'redroid-01:/sdcard/DCIM/Camera/sample_short.mp4'])
subprocess.run(['docker', 'cp', out_mp4, 'redroid-01:/sdcard/Movies/sample_short.mp4'])
subprocess.run(['docker', 'exec', 'redroid-01', 'chmod', '666', '/sdcard/DCIM/Camera/sample_short.mp4'])
subprocess.run(['docker', 'exec', 'redroid-01', 'chmod', '666', '/sdcard/Movies/sample_short.mp4'])

# Trigger MediaScanner to index the file
subprocess.run(['docker', 'exec', 'redroid-01', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', 'file:///sdcard/DCIM/Camera/sample_short.mp4'])
subprocess.run(['docker', 'exec', 'redroid-01', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', 'file:///sdcard/Movies/sample_short.mp4'])

print("Video generated and indexed successfully!")
