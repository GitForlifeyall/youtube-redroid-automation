import time, os, sys
sys.path.insert(0, os.path.abspath('.'))
from upload_short import run_adb, dump_ui_nodes, find_node, find_tool, DEFAULT_ADB

adb = find_tool('adb', DEFAULT_ADB)
target = '127.0.0.1:5801'

# The current screen is already open on adjust sound!
print('=== TESTING WAVEFORM SWIPE ON Y=960 ===')
# Read starting position
nodes = dump_ui_nodes(adb, target)
pos = find_node(nodes, res_id='play_position_text')
pos_str = pos['text'] if pos else 'None'
print(f'Starting Position: {pos_str}')

# Test small swipes to see how many seconds shift per pixel
for swipe_dx in [20, 40, 60, 80]:
    # Swiping left moves audio forward!
    run_adb(adb, target, 'shell', 'input', 'swipe', '400', '960', str(400 - swipe_dx), '960', '300')
    time.sleep(1.2)
    nodes = dump_ui_nodes(adb, target)
    pos = find_node(nodes, res_id='play_position_text')
    pos_str = pos['text'] if pos else 'None'
    print(f'Swipe dx={swipe_dx}px -> New Position: {pos_str}')
