import urllib.request, json, os

headers = {'User-Agent': 'Mozilla/5.0'}
try:
    req = urllib.request.Request('https://api.github.com/repos/MindTheGapps/14.0.0-arm64/releases', headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        for rel in data:
            for asset in rel.get('assets', []):
                print(asset['name'], asset['browser_download_url'])
except Exception as e:
    print('MindTheGapps Error:', e)

# Also check NikGapps
try:
    req = urllib.request.Request('https://api.github.com/repos/NikGapps/releases/releases/latest', headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        for asset in data.get('assets', []):
            print('NikGapps:', asset['name'], asset['browser_download_url'])
except Exception as e:
    print('NikGapps Error:', e)
