import urllib.request, os, subprocess

url = "https://github.com/j-hc/revanced-magisk-module/releases/download/20221085/youtube-morphe-v21.13.164-all.apk"
out_path = "/tmp/youtube_21.apk"

print("Downloading YouTube v21.13.164...")
headers = {'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp, open(out_path, 'wb') as out:
    out.write(resp.read())

print(f"Downloaded! Size: {os.path.getsize(out_path)} bytes")

os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
subprocess.run(['docker', 'cp', out_path, 'redroid-01:/data/local/tmp/youtube_21.apk'])
res = subprocess.run(['docker', 'exec', 'redroid-01', 'pm', 'install', '-r', '-d', '-g', '/data/local/tmp/youtube_21.apk'], capture_output=True, text=True)
print("PM Install Result:", res.stdout.strip(), res.stderr.strip())
