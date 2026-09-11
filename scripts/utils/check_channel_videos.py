import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ADB = r"C:\Users\Shahid\tools\scrcpy\adb.exe"
TARGET = "127.0.0.1:5801"

def run_adb(*args):
    cmd = [ADB, "-s", TARGET] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, errors="ignore")

def dump_ui():
    run_adb("shell", "uiautomator", "dump", "/sdcard/dump.xml")
    res = run_adb("shell", "cat", "/sdcard/dump.xml")
    if not res.stdout or "<hierarchy" not in res.stdout:
        return []
    try:
        root = ET.fromstring(res.stdout)
        nodes = []
        for elem in root.iter("node"):
            bounds_str = elem.attrib.get("bounds", "")
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            else:
                cx, cy = None, None
            nodes.append({
                "text": elem.attrib.get("text", ""),
                "desc": elem.attrib.get("content-desc", ""),
                "res_id": elem.attrib.get("resource-id", ""),
                "class": elem.attrib.get("class", ""),
                "cx": cx,
                "cy": cy,
                "bounds": (x1, y1, x2, y2) if m else None
            })
        return nodes
    except Exception:
        return []

def find_node(nodes, text=None, desc=None, res_id=None, min_x=0, min_y=0):
    for n in nodes:
        if n["cx"] is not None and n["cx"] < min_x:
            continue
        if n["cy"] is not None and n["cy"] < min_y:
            continue
        if text and text.lower() in n["text"].lower():
            return n
        if desc and desc.lower() in n["desc"].lower():
            return n
        if res_id and res_id.lower() in n["res_id"].lower():
            return n
    return None

def check_videos():
    # 1. Bring YouTube to front and ensure clean state
    print("[*] Launching YouTube App...", flush=True)
    run_adb("shell", "am", "start", "-n", "app.morphe.android.youtube/.morphe_black_1")
    time.sleep(2)
    
    # Press back if any modal/overlay is open
    run_adb("shell", "input", "keyevent", "4")
    time.sleep(1)
    
    # Dismiss any dialogs
    nodes = dump_ui()
    announcement_btn = find_node(nodes, text="OK") or find_node(nodes, text="Dismiss") or find_node(nodes, text="Ignore")
    if announcement_btn and announcement_btn["cx"]:
        print(f"[*] Dismissing dialog ('{announcement_btn['text']}') at ({announcement_btn['cx']}, {announcement_btn['cy']})...", flush=True)
        run_adb("shell", "input", "tap", str(announcement_btn["cx"]), str(announcement_btn["cy"]))
        time.sleep(1)
        nodes = dump_ui()
    
    # 2. Tap 'You' in bottom right
    you_btn = find_node(nodes, desc="You", min_x=500, min_y=1050) or find_node(nodes, text="You", min_x=500, min_y=1050)
    if you_btn and you_btn["cx"]:
        print(f"[+] Tapping 'You' tab at ({you_btn['cx']}, {you_btn['cy']})...", flush=True)
        run_adb("shell", "input", "tap", str(you_btn["cx"]), str(you_btn["cy"]))
    else:
        print("[*] Tapping default 'You' coords (648, 1136)...", flush=True)
        run_adb("shell", "input", "tap", "648", "1136")
    time.sleep(2)
    
    # 3. Scroll down on You page
    print("[*] Scrolling down on 'You' page...", flush=True)
    run_adb("shell", "input", "swipe", "360", "900", "360", "400", "300")
    time.sleep(2)
    
    # 4. Tap 'Your videos'
    nodes = dump_ui()
    your_videos = find_node(nodes, text="Your videos") or find_node(nodes, desc="Your videos")
    if your_videos and your_videos["cx"]:
        print(f"[+] Tapping 'Your videos' at ({your_videos['cx']}, {your_videos['cy']})...", flush=True)
        run_adb("shell", "input", "tap", str(your_videos["cx"]), str(your_videos["cy"]))
    else:
        print("[*] Tapping default 'Your videos' coords (227, 696)...", flush=True)
        run_adb("shell", "input", "tap", "227", "696")
    time.sleep(3)
    
    # 5. Count videos on 'Your videos' page
    nodes = dump_ui()
    videos = []
    for n in nodes:
        desc = n["desc"]
        if desc and ("views" in desc or "play Short" in desc or "play video" in desc):
            if desc not in videos:
                videos.append(desc)
    
    print(f"\n[+] Total videos found in 'Your videos': {len(videos)}", flush=True)
    for i, v in enumerate(videos, 1):
        print(f"  {i}. {v}", flush=True)
    
    return len(videos)

if __name__ == "__main__":
    count = check_videos()
    if count > 2:
        print(f"\n[SUCCESS] Video count ({count}) is MORE THAN 2! Script is working!", flush=True)
    else:
        print(f"\n[*] Current video count: {count} (Target: > 2)", flush=True)
