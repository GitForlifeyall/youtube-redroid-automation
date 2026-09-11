import zipfile, os, subprocess

os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'

with zipfile.ZipFile('/tmp/mindthegapps.zip', 'r') as z:
    for f in z.namelist():
        if f.endswith('.apk'):
            print('GApps APK:', f)
            z.extract(f, '/tmp/gapps_out')
            host_path = os.path.join('/tmp/gapps_out', f)
            apk_name = os.path.basename(f)
            subprocess.run(['docker', 'cp', host_path, f'redroid-01:/data/local/tmp/{apk_name}'])
            res = subprocess.run(['docker', 'exec', 'redroid-01', 'pm', 'install', '-r', '-d', '-g', f'/data/local/tmp/{apk_name}'], capture_output=True, text=True)
            print(f'Install {apk_name}: {res.stdout.strip()} {res.stderr.strip()}')
