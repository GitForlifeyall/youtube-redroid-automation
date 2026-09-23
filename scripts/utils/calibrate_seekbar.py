import time, os, sys
sys.path.insert(0, os.path.abspath('.'))
from upload_short import run_adb, dump_ui_nodes, find_node, push_and_index_video, find_tool, DEFAULT_ADB

adb = find_tool('adb', DEFAULT_ADB)
target = '127.0.0.1:5801'
yt_pkg = 'app.morphe.android.youtube'

# Push & start trimmer -> Editor -> Add Sound
uri = push_and_index_video(adb, target, 'downloads/test_short.mp4')
run_adb(adb, target, 'shell', 'am', 'force-stop', yt_pkg)
time.sleep(1.5)
run_adb(adb, target, 'shell', 'am', 'start', '-n', f'{yt_pkg}/com.google.android.apps.youtube.app.application.Shell_UploadActivity', '-d', uri, '-a', 'android.intent.action.SEND', '-t', 'video/mp4', '--eu', 'android.intent.extra.STREAM', uri)
time.sleep(3)
run_adb(adb, target, 'shell', 'input', 'tap', '627', '1112')
time.sleep(3)
run_adb(adb, target, 'shell', 'input', 'tap', '360', '120')
time.sleep(2)
run_adb(adb, target, 'shell', 'input', 'tap', '360', '212')
time.sleep(0.8)
run_adb(adb, target, 'shell', 'input', 'text', 'Sunflower')
run_adb(adb, target, 'shell', 'input', 'keyevent', '66')
time.sleep(2.5)
run_adb(adb, target, 'shell', 'input', 'tap', '360', '470')
time.sleep(1.5)
run_adb(adb, target, 'shell', 'input', 'tap', '648', '460')
time.sleep(2)

# Open adjust sound modal
run_adb(adb, target, 'shell', 'input', 'tap', '360', '120')
time.sleep(2)

print('=== TESTING SEEKBAR X COORDINATES ===')
for x in [390, 400, 405, 410, 415, 420, 425]:
    run_adb(adb, target, 'shell', 'input', 'tap', str(x), '832')
    time.sleep(1.2)
    nodes = dump_ui_nodes(adb, target)
    pos = find_node(nodes, res_id='play_position_text')
    dur = find_node(nodes, res_id='audio_duration_text')
    pos_str = pos['text'] if pos else 'None'
    dur_str = dur['text'] if dur else 'None'
    print(f'Tap X={x} -> Position: {pos_str} (Total: {dur_str})')
