import subprocess, os

os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'

# Scan file using media scan
subprocess.run(['docker', 'exec', 'redroid-01', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', 'file:///sdcard/DCIM/Camera/sample_short.mp4'])

# Query content provider
res = subprocess.check_output(['docker', 'exec', 'redroid-01', 'content', 'query', '--uri', 'content://media/external/video/media']).decode()
print("Media query result:\n", res)

# If not found, insert via content insert
if 'sample_short.mp4' not in res:
    insert_cmd = [
        'docker', 'exec', 'redroid-01', 'content', 'insert',
        '--uri', 'content://media/external/video/media',
        '--bind', '_data:s:/storage/emulated/0/DCIM/Camera/sample_short.mp4',
        '--bind', 'title:s:Sample Short',
        '--bind', 'mime_type:s:video/mp4'
    ]
    ires = subprocess.check_output(insert_cmd).decode()
    print("Insert result:", ires)
    res = subprocess.check_output(['docker', 'exec', 'redroid-01', 'content', 'query', '--uri', 'content://media/external/video/media']).decode()
    print("New query result:\n", res)
