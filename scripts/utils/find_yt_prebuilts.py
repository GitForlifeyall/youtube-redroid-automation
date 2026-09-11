import urllib.request, json, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

# Let's check Github releases for ReVanced YouTube or YouTube Extended APKs (official package or patched)
try:
    req = urllib.request.Request('https://api.github.com/repos/inotia00/VancedMicroG/releases/latest', headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        print('MicroG:', resp.status)
except Exception as e:
    print('MicroG Error:', e)

# Check ReVanced / ReVanced Extended prebuilts or ReVanced CLI
try:
    req = urllib.request.Request('https://api.github.com/repos/j-hc/revanced-magisk-module/releases/latest', headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        for a in data.get('assets', []):
            print('ReVanced Asset:', a['name'], a['browser_download_url'])
except Exception as e:
    print('ReVanced Error:', e)
