import urllib.request, json, os, subprocess

headers = {'User-Agent': 'Mozilla/5.0'}

# Find ReVanced GmsCore
url = 'https://api.github.com/repos/ReVanced/GmsCore/releases/latest'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    for a in data.get('assets', []):
        if a['name'].endswith('.apk'):
            print('GmsCore asset:', a['name'], a['browser_download_url'])
            # Download and install
            out_file = '/tmp/' + a['name']
            r = urllib.request.Request(a['browser_download_url'], headers=headers)
            with urllib.request.urlopen(r) as dresp, open(out_file, 'wb') as out:
                out.write(dresp.read())
            print('Downloaded', a['name'])
            os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
            subprocess.run(['docker', 'cp', out_file, f'redroid-01:/data/local/tmp/{a["name"]}'])
            res = subprocess.run(['docker', 'exec', 'redroid-01', 'pm', 'install', '-r', '-d', '-g', f'/data/local/tmp/{a["name"]}'], capture_output=True, text=True)
            print('PM Result:', res.stdout.strip(), res.stderr.strip())
