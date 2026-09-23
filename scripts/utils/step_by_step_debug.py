import os
import sys
import time
import subprocess
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ADB = r"C:\Users\Shahid\tools\scrcpy\adb.exe"
TARGET = "127.0.0.1:5555"
VIDEO_PATH = r"upload files\short_10s_test.mp4"
TITLE = "Test Short Sound & Waveform"
SOUND_QUERY = "sunflower"
TIMESTAMP = "0:30"
DEBUG_DIR = Path("debug/step_debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

def adb_shell(*args) -> str:
    cmd = [ADB, "-s", TARGET, "shell"] + list(args)
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout.strip()

def screenshot(name: str) -> str:
    out_path = DEBUG_DIR / f"{name}.png"
    temp_remote = "/sdcard/screen.png"
    adb_shell("screencap", "-p", temp_remote)
    subprocess.run([ADB, "-s", TARGET, "pull", temp_remote, str(out_path)], capture_output=True)
    print(f"  [SCREENSHOT] Saved: {out_path}")
    return str(out_path)

def dump_ui() -> tuple[Optional[ET.Element], str]:
    adb_shell("uiautomator", "dump", "--compressed", "/sdcard/ui_dump.xml")
    xml_data = adb_shell("cat", "/sdcard/ui_dump.xml")
    if xml_data and "<hierarchy" in xml_data:
        clean_xml = xml_data[xml_data.find("<hierarchy"):]
        try:
            return ET.fromstring(clean_xml), clean_xml
        except Exception:
            pass
    return None, xml_data

def tap(x: int, y: int, desc: str = ""):
    print(f"  [TAP] ({x}, {y}) {desc}")
    adb_shell("input", "tap", str(x), str(y))

def click_node(node: ET.Element, desc: str = ""):
    bounds = node.attrib.get("bounds", "[0,0][0,0]")
    matches = re.findall(r"\[(\d+),(\d+)\]", bounds)
    if len(matches) == 2:
        x = (int(matches[0][0]) + int(matches[1][0])) // 2
        y = (int(matches[0][1]) + int(matches[1][1])) // 2
        tap(x, y, desc or node.attrib.get("text", "") or node.attrib.get("content-desc", ""))

def find_first_node(root: ET.Element, *query_dicts) -> Optional[ET.Element]:
    if root is None:
        return None
    for q in query_dicts:
        for node in root.iter("node"):
            match = True
            for key, val in q.items():
                attr = node.attrib.get(key, "")
                if isinstance(val, re.Pattern):
                    if not val.search(attr):
                        match = False
                        break
                elif val.lower() not in attr.lower():
                    match = False
                    break
            if match:
                return node
    return None

def main():
    print("=== STARTING STEP-BY-STEP UPLOAD DEBUGGING ===")
    
    # Check device
    subprocess.run([ADB, "connect", TARGET], capture_output=True)
    adb_shell("wm", "size", "720x1280")
    adb_shell("wm", "density", "320")
    
    # 1. Push video & get content URI
    print("\n--- STEP 1: Push Video & Resolve URI ---")
    remote_path = f"/sdcard/DCIM/Camera/debug_short_{int(time.time())}.mp4"
    adb_shell("mkdir", "-p", "/sdcard/DCIM/Camera")
    subprocess.run([ADB, "-s", TARGET, "push", VIDEO_PATH, remote_path], check=True, capture_output=True)
    adb_shell("am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_path}")
    time.sleep(1.5)
    
    q_res = adb_shell("content", "query", "--uri", "content://media/external/video/media", "--projection", "_id:_data")
    ids = re.findall(r"_id=(\d+)", q_res)
    uri = f"content://media/external/video/media/{ids[-1]}" if ids else f"file://{remote_path}"
    print(f"  [+] Media URI: {uri}")
    
    # 2. Launch YouTube Upload Intent
    print("\n--- STEP 2: Launch YouTube Upload Intent ---")
    pkg = "app.revanced.android.youtube"
    adb_shell("am", "force-stop", pkg)
    time.sleep(1)
    
    adb_shell("am", "start",
              "-n", f"{pkg}/com.google.android.apps.youtube.app.application.Shell_UploadActivity",
              "-d", uri,
              "-a", "android.intent.action.SEND",
              "-t", "video/mp4",
              "--eu", "android.intent.extra.STREAM", uri)
    time.sleep(3.5)
    screenshot("01_after_launch")
    
    root, _ = dump_ui()
    
    # Check what screen we are on
    # In Step 1: Is there a "Done" or "Next" button?
    print("\n--- STEP 3: Handle Trim / Import Screen ---")
    btn = find_first_node(root, {"text": "Done"}, {"content_desc": "Done"}, {"text": "Next"}, {"content_desc": "Next"})
    if btn is not None:
        print(f"  Found button: text='{btn.attrib.get('text')}' desc='{btn.attrib.get('content-desc')}' bounds={btn.attrib.get('bounds')}")
        click_node(btn, "Trim screen confirm")
    else:
        print("  Fallback: tapping bottom right (640, 940) or (640, 1200)")
        tap(640, 940, "Trim Done fallback")
    
    print("  Waiting 4s for video processing...")
    time.sleep(4)
    screenshot("02_after_trim_processing")
    
    # Check if we are in Editor Screen (Screen with "Add sound")
    print("\n--- STEP 4: Shorts Editor Screen & Add Sound ---")
    root, _ = dump_ui()
    sound_btn = find_first_node(root, {"text": re.compile(r"Add sound", re.I)}, {"content_desc": re.compile(r"Add sound", re.I)})
    if sound_btn is not None:
        print(f"  Found sound button: text='{sound_btn.attrib.get('text')}' desc='{sound_btn.attrib.get('content-desc')}' bounds={sound_btn.attrib.get('bounds')}")
        click_node(sound_btn, "Add sound")
    else:
        print("  Fallback: tap (360, 90)")
        tap(360, 90, "Add sound top center")
    
    time.sleep(3)
    screenshot("03_sound_library_open")
    
    # Search Sound
    print("\n--- STEP 5: Search Sound ---")
    root, _ = dump_ui()
    search_btn = find_first_node(root, {"content_desc": re.compile(r"Search", re.I)}, {"resource_id": re.compile(r"search", re.I)})
    if search_btn is not None:
        print(f"  Found search button: bounds={search_btn.attrib.get('bounds')}")
        click_node(search_btn, "Search sound")
    else:
        tap(660, 80, "Search button top right")
    time.sleep(1.5)
    screenshot("04_sound_search_opened")
    
    print(f"  Typing search query '{SOUND_QUERY}'...")
    adb_shell("input", "text", SOUND_QUERY.replace(" ", "%s"))
    adb_shell("input", "keyevent", "66") # ENTER
    time.sleep(3.5)
    screenshot("05_sound_search_results")
    
    # Select Top Track
    print("\n--- STEP 6: Select Top Track & Confirm ---")
    root, _ = dump_ui()
    first_track = find_first_node(root, {"resource_id": re.compile(r"audio_pivot_item|track_item|item_container|audio_track", re.I)})
    if first_track is not None:
        print(f"  Found track: bounds={first_track.attrib.get('bounds')}")
        click_node(first_track, "First track")
    else:
        tap(360, 260, "Top track item")
    time.sleep(2)
    screenshot("06_track_selected")
    
    root, _ = dump_ui()
    use_btn = find_first_node(root, {"content_desc": re.compile(r"Use this sound|Select this sound|Arrow", re.I)})
    if use_btn is not None:
        print(f"  Found use button: bounds={use_btn.attrib.get('bounds')}")
        click_node(use_btn, "Use sound button")
    else:
        tap(640, 260, "Use sound arrow")
    time.sleep(3.5)
    screenshot("07_after_sound_added")
    
    # Timestamp / Adjust waveform
    print("\n--- STEP 7: Adjust Audio Waveform ---")
    root, _ = dump_ui()
    adjust_btn = find_first_node(root, {"text": re.compile(r"Adjust|Trim", re.I)}, {"content_desc": re.compile(r"Adjust|Trim", re.I)})
    if adjust_btn is not None:
        print(f"  Found adjust button: bounds={adjust_btn.attrib.get('bounds')}")
        click_node(adjust_btn, "Adjust button")
    else:
        tap(680, 480, "Adjust button right sidebar")
    time.sleep(2)
    screenshot("08_waveform_editor")
    
    # Scrub waveform: for 30s in 60s track, ~ middle (395, 1120)
    print("  Scrubbing waveform...")
    tap(395, 1120, "Waveform scrub to 30s")
    time.sleep(1)
    
    root, _ = dump_ui()
    done_btn = find_first_node(root, {"text": "Done"}, {"content_desc": "Done"})
    if done_btn is not None:
        click_node(done_btn, "Waveform Done")
    else:
        tap(640, 1220, "Waveform Done bottom right")
    time.sleep(2.5)
    screenshot("09_waveform_confirmed")
    
    # Click Next in Editor
    print("\n--- STEP 8: Proceed to Details Screen (Next) ---")
    root, _ = dump_ui()
    next_btn = find_first_node(root, {"text": "Next"}, {"content_desc": "Next"})
    if next_btn is not None:
        print(f"  Found Next button: bounds={next_btn.attrib.get('bounds')}")
        click_node(next_btn, "Editor Next")
    else:
        tap(540, 1220, "Editor Next bottom right")
    
    print("  Waiting 4s for details screen & thumbnail generation...")
    time.sleep(4)
    screenshot("10_details_screen")
    
    # Title Entry
    print("\n--- STEP 9: Enter Title / Caption ---")
    root, _ = dump_ui()
    title_box = find_first_node(root, {"text": re.compile(r"Caption your Short|Title", re.I)}, {"resource_id": re.compile(r"title|caption", re.I)})
    if title_box is not None:
        print(f"  Found Title box: bounds={title_box.attrib.get('bounds')}")
        click_node(title_box, "Title box")
    else:
        tap(450, 180, "Caption your short box")
    time.sleep(1.5)
    
    safe_title = TITLE.replace(" ", "%s").replace("'", "\\'")
    adb_shell("input", "text", safe_title)
    time.sleep(1)
    adb_shell("input", "keyevent", "111") # Hide keyboard
    time.sleep(1.5)
    screenshot("11_title_entered")
    
    # Click Upload Short
    print("\n--- STEP 10: Click Upload Short ---")
    root, _ = dump_ui()
    upload_btn = find_first_node(root, {"text": re.compile(r"Upload Short", re.I)}, {"content_desc": re.compile(r"Upload Short", re.I)})
    if upload_btn is not None:
        print(f"  Found Upload Short button: bounds={upload_btn.attrib.get('bounds')}")
        click_node(upload_btn, "Upload Short button")
    else:
        tap(360, 940, "Upload Short button")
    
    time.sleep(4)
    screenshot("12_upload_dispatched")
    
    # Verification in Your videos
    print("\n--- STEP 11: Verification in 'Your videos' ---")
    adb_shell("monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(3)
    
    root, _ = dump_ui()
    you = find_first_node(root, {"text": "You"}, {"content_desc": "You"})
    if you is not None:
        click_node(you, "You tab")
    else:
        tap(640, 1230, "You tab bottom right")
    time.sleep(2)
    
    root, _ = dump_ui()
    your_vids = find_first_node(root, {"text": "Your videos"}, {"content_desc": "Your videos"})
    if your_vids is not None:
        click_node(your_vids, "Your videos button")
    else:
        tap(250, 480, "Your videos button")
    time.sleep(3)
    screenshot("13_your_videos_screen")
    
    print("\n=== DEBUG RUN FINISHED ===")

if __name__ == "__main__":
    main()
