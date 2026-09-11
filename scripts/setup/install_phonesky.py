import urllib.request, zipfile, os, subprocess

url = 'https://github.com/MindTheGapps/14.0.0-arm64/releases/download/MindTheGapps-14.0.0-arm64-20250203_200051/MindTheGapps-14.0.0-arm64-20250203_200051.zip'
zip_path = '/tmp/mindthegapps.zip'

if not os.path.exists(zip_path):
    print('Downloading MindTheGapps...')
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(zip_path, 'wb') as out:
        out.write(resp.read())
    print('Downloaded.')

os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'

with zipfile.ZipFile(zip_path, 'r') as z:
    for name in z.namelist():
        if 'Phonesky' in name and name.endswith('.apk'):
            print('Found Phonesky:', name)
            z.extract(name, '/tmp/gapps_out')
            apk_path = os.path.join('/tmp/gapps_out', name)
            # Install to redroid
            print('Installing Phonesky to redroid-01...')
            out = subprocess.check_output(['docker', 'exec', 'redroid-01', 'pm', 'install', '-r', '-d', apk_path if not os.path.isabs(apk_path) else apk_path], stderr=subprocess.STDOUT)
            print('Install output:', out.decode())
        elif 'GoogleServicesFramework' in name and name.endswith('.apk'):
            print('Found GSF:', name)
            z.extract(name, '/tmp/gapps_out')
            apk_path = os.path.join('/tmp/gapps_out', name)
            try:
                out = subprocess.check_output(['docker', 'exec', 'redroid-01', 'pm', 'install', '-r', '-d', apk_path], stderr=subprocess.STDOUT)
                print('GSF output:', out.decode())
            except Exception as e:
                print('GSF error:', e)
