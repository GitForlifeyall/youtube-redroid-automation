import zipfile, os, subprocess

os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'

# First uninstall user-installed versions from pm so system versions take over
for pkg in ['com.google.android.gsf', 'com.google.android.gms', 'com.android.vending', 'com.google.android.googlequicksearchbox']:
    try:
        subprocess.run(['docker', 'exec', 'redroid-01', 'pm', 'uninstall', pkg])
    except Exception as e:
        pass

# Extract all system/ from mindthegapps.zip
with zipfile.ZipFile('/tmp/mindthegapps.zip', 'r') as z:
    for name in z.namelist():
        if name.startswith('system/') and not name.endswith('/'):
            target_path = '/' + name # e.g. /system/product/priv-app/...
            print('Deploying:', target_path)
            z.extract(name, '/tmp/mtg_extract')
            local_file = os.path.join('/tmp/mtg_extract', name)
            # Create remote dir
            remote_dir = os.path.dirname(target_path)
            subprocess.run(['docker', 'exec', 'redroid-01', 'mkdir', '-p', remote_dir])
            subprocess.run(['docker', 'cp', local_file, f'redroid-01:{target_path}'])
            subprocess.run(['docker', 'exec', 'redroid-01', 'chmod', '644', target_path])

print('Done deploying MindTheGapps system files.')
