import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from upload_short import run_adb, dump_ui_nodes, find_node, push_and_index_video, find_tool, DEFAULT_ADB

adb = find_tool('adb', DEFAULT_ADB)
target = '127.0.0.1:5801'
yt_pkg = 'app.morphe.android.youtube'

# Push & start trimmer
uri = push_and_index_video(adb, target, 'downloads/test_short.mp4')
run_adb(adb, target, 'shell', 'am', 'force-stop', yt_pkg)
time.sleep(2)
run_adb(adb, target, 'shell', 'am', 'start', '-n', f'{yt_pkg}/com.google.android.apps.youtube.app.application.Shell_UploadActivity', '-d', uri, '-a', 'android.intent.action.SEND', '-t', 'video/mp4', '--eu', 'android.intent.extra.STREAM', uri)
time.sleep(6)

# Trimmer -> Next
print('[*] Tapping trimmer Next...')
run_adb(adb, target, 'shell', 'input', 'tap', '627', '1112')
time.sleep(6)

# Editor -> Add sound
print('[*] Tapping Add sound...')
run_adb(adb, target, 'shell', 'input', 'tap', '360', '120')
time.sleep(4)

# Tap search box
print('[*] Tapping Search box...')
run_adb(adb, target, 'shell', 'input', 'tap', '360', '212')
time.sleep(2)

# Type 'Sunflower'
print('[*] Typing Sunflower...')
run_adb(adb, target, 'shell', 'input', 'text', 'Sunflower')
time.sleep(1)
run_adb(adb, target, 'shell', 'input', 'keyevent', '66')
time.sleep(5)

# Tap search result item
print('[*] Tapping first search item at (300, 380)...')
run_adb(adb, target, 'shell', 'input', 'tap', '300', '380')
time.sleep(3)

# Dump UI nodes
nodes = dump_ui_nodes(adb, target)
print(f'Found {len(nodes)} nodes after tapping search item:')
for n in nodes:
    if n['desc'] or n['text'] or n['res_id']:
        print(f"[{n['bounds']}]: text='{n['text']}' desc='{n['desc']}' id='{n['res_id']}'")

run_adb(adb, target, 'shell', 'screencap', '-p', '/sdcard/item_clicked.png')
run_adb(adb, target, 'pull', '/sdcard/item_clicked.png', '.')
