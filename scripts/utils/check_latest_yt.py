import urllib.request, json, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Check APKPure for YouTube latest version
try:
    req = urllib.request.Request('https://apkpure.com/youtube/com.google.android.youtube/versions', headers=headers)
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        versions = re.findall(r'/youtube/com\.google\.android\.youtube/download/([0-9\.\-]+)', html)
        print('APKPure Versions:', set(versions[:10]))
except Exception as e:
    print('APKPure Error:', e)

# Also check if apkpure API or uptodown has latest
try:
    req = urllib.request.Request('https://youtube.en.uptodown.com/android/versions', headers=headers)
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        versions = re.findall(r'data-version="([^"]+)"', html)
        print('Uptodown Versions:', versions[:10])
except Exception as e:
    print('Uptodown Error:', e)
