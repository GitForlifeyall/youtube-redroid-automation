import time, os, sys
sys.path.insert(0, os.path.abspath('.'))
from upload_short import run_adb, dump_ui_nodes, find_node, parse_timestamp_seconds, find_tool, DEFAULT_ADB

adb = find_tool('adb', DEFAULT_ADB)
target = '127.0.0.1:5801'

target_ts = '1:30'
target_sec = parse_timestamp_seconds(target_ts)

print(f'=== TESTING EXACT SEEK TO {target_ts} ({target_sec}s) ===')

# Read duration
nodes = dump_ui_nodes(adb, target)
dur_node = find_node(nodes, res_id='audio_duration_text')
dur_sec = parse_timestamp_seconds(dur_node['text']) if dur_node else 158.0
print(f'Total Duration: {dur_sec}s')

# 1. Coarse seek on seekbar
ratio = min(1.0, max(0.0, target_sec / dur_sec))
tap_x = int(96 + ratio * 528)
run_adb(adb, target, 'shell', 'input', 'tap', str(tap_x), '832')
time.sleep(1.2)

# 2. Micro-adjust on waveform (y=960)
for step in range(3):
    nodes = dump_ui_nodes(adb, target)
    pos_node = find_node(nodes, res_id='play_position_text')
    pos_str = pos_node['text'] if pos_node else 'None'
    curr_sec = parse_timestamp_seconds(pos_str) if pos_node else 0.0
    diff_sec = target_sec - curr_sec
    print(f'Step {step+1}: Current={pos_str} ({curr_sec}s), Diff={diff_sec:+.1f}s')
    
    if abs(diff_sec) < 0.5:
        print(f'[SUCCESS] Hit exact target timestamp {target_ts}!')
        break
    
    # 1 second = ~85px on waveform
    swipe_dx = int(diff_sec * 85)
    # Clamp to avoid swiping offscreen
    swipe_dx = max(-300, min(300, swipe_dx))
    start_x = 360
    end_x = start_x - swipe_dx
    print(f'  Micro-adjusting waveform: swipe from {start_x} to {end_x} on y=960...')
    run_adb(adb, target, 'shell', 'input', 'swipe', str(start_x), '960', str(end_x), '960', '250')
    time.sleep(1.2)
