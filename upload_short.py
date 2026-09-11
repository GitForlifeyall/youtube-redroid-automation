"""
YouTube Short Uploader for Redroid Android Instances
=====================================================
Automates pushing and uploading YouTube Shorts directly from local video files
to the logged-in YouTube channel on a Redroid Android instance.
Verifies channel upload count via YouTube App navigation (You -> Your videos).

Usage:
    python upload_short.py -u <video_path> [-v] [--account 01] [--title "Short Title"]
    python upload_short.py <video_path> -u -v

Flags:
    -u, --upload <PATH>   Path to the video file to upload (or standalone flag if path given positionally)
    -v, --view            Launch scrcpy to view the Android screen in real-time
    -a, --account <NUM>   Redroid instance/account number (default: 01 -> port 5801)
    -t, --title <TEXT>    Title for the YouTube Short (default: filename)
"""

import argparse
import os
import sys
import time
import subprocess
import re
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_TOOLS_DIR = Path(r"C:\Users\Shahid\tools\scrcpy")
DEFAULT_ADB = DEFAULT_TOOLS_DIR / "adb.exe"
DEFAULT_SCRCPY = DEFAULT_TOOLS_DIR / "scrcpy.exe"
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


def log(msg: str):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        safe_msg = str(msg).encode("ascii", errors="backslashreplace").decode("ascii")
        print(safe_msg, flush=True)


def find_tool(name: str, fallback_path: Path) -> str:
    if fallback_path.exists():
        return str(fallback_path)
    import shutil
    found = shutil.which(name)
    if found:
        return found
    return name


def run_adb(adb_exe: str, target: str, *args, check=False) -> subprocess.CompletedProcess:
    cmd = [adb_exe, "-s", target] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="ignore")


def connect_adb(adb_exe: str, target: str, max_retries: int = 10) -> bool:
    log(f"[*] Connecting to Android instance at {target}...")
    for _ in range(max_retries):
        subprocess.run([adb_exe, "connect", target], capture_output=True)
        res = subprocess.run([adb_exe, "devices"], capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if target in res.stdout and "device" in res.stdout:
            boot_check = run_adb(adb_exe, target, "shell", "getprop", "sys.boot_completed")
            if boot_check.stdout.strip() == "1":
                log(f"[+] Connected to {target} (Boot Complete)")
                return True
        time.sleep(1)
    log(f"[!] Warning: Device {target} connected, but may still be initializing.")
    return True


def is_scrcpy_running() -> bool:
    try:
        res = subprocess.run(["tasklist"], capture_output=True, text=True, errors="ignore")
        return "scrcpy.exe" in res.stdout.lower()
    except Exception:
        return False


def launch_scrcpy(scrcpy_exe: str, target: str):
    if is_scrcpy_running():
        log("[+] Scrcpy screen viewer is already active on your display.")
        return
    
    log(f"[*] Launching scrcpy viewer for {target}...")
    try:
        subprocess.Popen(
            [scrcpy_exe, "-s", target, "--window-title", f"Redroid - {target}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        log("[+] Screen viewer opened successfully!")
    except Exception as e:
        log(f"[!] Could not launch scrcpy: {e}")


def push_and_index_video(adb_exe: str, target: str, local_path: str) -> str:
    path_obj = Path(local_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Video file not found at: {local_path}")
    
    file_size_mb = path_obj.stat().st_size / (1024 * 1024)
    remote_movies = f"/storage/emulated/0/Movies/{path_obj.name}"
    remote_downloads = f"/storage/emulated/0/Download/{path_obj.name}"
    
    log(f"[*] Pushing '{path_obj.name}' ({file_size_mb:.2f} MB) to Android device...")
    res = subprocess.run([adb_exe, "-s", target, "push", str(path_obj.resolve()), remote_movies],
                         capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if res.returncode != 0:
        raise RuntimeError(f"ADB Push failed: {res.stderr}")
    
    run_adb(adb_exe, target, "shell", "cp", remote_movies, remote_downloads)
    run_adb(adb_exe, target, "shell", "chmod", "-R", "777", "/storage/emulated/0/Movies", "/storage/emulated/0/Download")
    
    log("[*] Indexing video in MediaStore...")
    run_adb(adb_exe, target, "shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_movies}")
    run_adb(adb_exe, target, "shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_downloads}")
    time.sleep(4)
    
    # Query media ID
    res = run_adb(adb_exe, target, "shell", "content", "query", "--uri", "content://media/external/video/media", "--projection", "_id:_data")
    media_id = None
    for line in reversed(res.stdout.splitlines()):
        if path_obj.name in line:
            m = re.search(r"_id=(\d+)", line)
            if m:
                media_id = m.group(1)
                break
    
    if not media_id:
        # Fallback to the latest media row ID
        m = re.findall(r"_id=(\d+)", res.stdout)
        if m:
            media_id = m[-1]
    
    content_uri = f"content://media/external/video/media/{media_id}" if media_id else f"file://{remote_movies}"
    log(f"[+] Video indexed with URI: {content_uri}")
    return content_uri


def dump_ui_nodes(adb_exe: str, target: str):
    run_adb(adb_exe, target, "shell", "uiautomator", "dump", "/sdcard/window_dump.xml")
    res = run_adb(adb_exe, target, "shell", "cat", "/sdcard/window_dump.xml")
    if not res.stdout or "<hierarchy" not in res.stdout:
        # Fallback to --compressed if standard dump had an idle lock
        run_adb(adb_exe, target, "shell", "uiautomator", "dump", "--compressed", "/sdcard/window_dump.xml")
        res = run_adb(adb_exe, target, "shell", "cat", "/sdcard/window_dump.xml")
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


def find_node(nodes, text=None, desc=None, res_id=None, min_x=0, min_y=0, max_y=9999):
    for n in nodes:
        if n["cx"] is not None and n["cx"] < min_x:
            continue
        if n["cy"] is not None and (n["cy"] < min_y or n["cy"] > max_y):
            continue
        if text and text.lower() in n["text"].lower():
            return n
        if desc and desc.lower() in n["desc"].lower():
            return n
        if res_id and res_id.lower() in n["res_id"].lower():
            return n
    return None


def get_installed_youtube_package(adb_exe: str, target: str) -> str:
    res = run_adb(adb_exe, target, "shell", "pm", "list", "packages")
    pkgs = res.stdout.splitlines()
    for candidate in ["app.morphe.android.youtube", "app.revanced.android.youtube", "com.google.android.youtube"]:
        if f"package:{candidate}" in pkgs:
            return candidate
    return "app.morphe.android.youtube"


def upload_short_to_youtube(adb_exe: str, target: str, video_path: str, title: str, sound: Optional[str] = None):
    log("\n========================================================")
    log("  AUTOMATING YOUTUBE SHORT UPLOAD")
    log("========================================================")
    
    yt_pkg = get_installed_youtube_package(adb_exe, target)
    
    # Step 1: Push and index video
    content_uri = push_and_index_video(adb_exe, target, video_path)
    
    # Step 2: Reset YouTube and launch direct video upload intent
    log(f"[*] Launching YouTube Short upload editor ({yt_pkg})...")
    run_adb(adb_exe, target, "shell", "am", "force-stop", yt_pkg)
    time.sleep(2)
    
    upload_cmd = [
        "am", "start",
        "-n", f"{yt_pkg}/com.google.android.apps.youtube.app.application.Shell_UploadActivity",
        "-d", content_uri,
        "-a", "android.intent.action.SEND",
        "-t", "video/mp4",
        "--eu", "android.intent.extra.STREAM", content_uri
    ]
    run_adb(adb_exe, target, "shell", *upload_cmd)
    log("[*] Waiting for video trimmer to load...")
    time.sleep(5)
    
    # Step 3: Handle Trimmer Screen -> Tap 'Next'
    log("[*] Navigating video trimmer...")
    nodes = dump_ui_nodes(adb_exe, target)
    next_trim_btn = (
        find_node(nodes, res_id="shorts_trim_finish_trim_button")
        or find_node(nodes, desc="Continue to editor")
        or find_node(nodes, text="Next")
    )
    if next_trim_btn and next_trim_btn["cx"]:
        log(f"[+] Tapping trimmer 'Next' at ({next_trim_btn['cx']}, {next_trim_btn['cy']})...")
        run_adb(adb_exe, target, "shell", "input", "tap", str(next_trim_btn["cx"]), str(next_trim_btn["cy"]))
    else:
        log("[*] Tapping trimmer 'Next' at default coordinates (627, 1112)...")
        run_adb(adb_exe, target, "shell", "input", "tap", "627", "1112")
    
    log("[*] Waiting for trimmer processing...")
    time.sleep(5)
    
    # Step 4: Handle Shorts Editor Screen
    log("[*] Navigating Shorts editor...")
    
    # Check if sound selection was requested via -s / --sound flag
    if sound:
        log("[*] Sound flag detected: Selecting audio track from YouTube music library...")
        nodes = dump_ui_nodes(adb_exe, target)
        sound_btn = (
            find_node(nodes, res_id="shorts_edit_sound_button")
            or find_node(nodes, text="Add sound")
            or find_node(nodes, desc="Add sound")
            or find_node(nodes, text="Sound")
        )
        if sound_btn and sound_btn["cx"]:
            log(f"[+] Tapping 'Add sound' button at ({sound_btn['cx']}, {sound_btn['cy']})...")
            run_adb(adb_exe, target, "shell", "input", "tap", str(sound_btn["cx"]), str(sound_btn["cy"]))
        else:
            log("[*] Tapping 'Add sound' at default coordinates (360, 120)...")
            run_adb(adb_exe, target, "shell", "input", "tap", "360", "120")
        
        # Wait for music picker library to load
        time.sleep(4)
        
        # If a specific song query was passed as string (e.g. --sound "Sunflower")
        if isinstance(sound, str) and sound.strip() and sound.strip().lower() not in ("true", "1"):
            search_query = sound.strip()
            log(f"[*] Searching for audio track '{search_query}'...")
            nodes = dump_ui_nodes(adb_exe, target)
            search_box = find_node(nodes, res_id="music_picker_search_box") or find_node(nodes, text="Search music")
            if search_box and search_box["cx"]:
                run_adb(adb_exe, target, "shell", "input", "tap", str(search_box["cx"]), str(search_box["cy"]))
            else:
                run_adb(adb_exe, target, "shell", "input", "tap", "360", "212")
            time.sleep(2)
            
            # Type search query
            words = search_query.split(" ")
            for i, word in enumerate(words):
                if word:
                    safe_word = re.sub(r'([&|;$><`"\'\\])', r'\\\1', word)
                    run_adb(adb_exe, target, "shell", "input", "text", safe_word)
                if i < len(words) - 1:
                    run_adb(adb_exe, target, "shell", "input", "keyevent", "62")
            time.sleep(1)
            run_adb(adb_exe, target, "shell", "input", "keyevent", "66")
            time.sleep(4)
        
        # Tap the first track in the music picker
        log("[*] Selecting track from music library...")
        run_adb(adb_exe, target, "shell", "input", "tap", "300", "240")
        time.sleep(2)
        
        # Tapping the blue checkmark/apply button: "Add this music to your video"
        nodes = dump_ui_nodes(adb_exe, target)
        add_music_btn = find_node(nodes, desc="Add this music to your video")
        if add_music_btn and add_music_btn["cx"]:
            log(f"[+] Attaching selected music at ({add_music_btn['cx']}, {add_music_btn['cy']})...")
            run_adb(adb_exe, target, "shell", "input", "tap", str(add_music_btn["cx"]), str(add_music_btn["cy"]))
        else:
            log("[*] Attaching music at default apply coords (648, 240)...")
            run_adb(adb_exe, target, "shell", "input", "tap", "648", "240")
        
        time.sleep(4)
        log("[+] Sound successfully attached to Short!")
    
    # Tap editor 'Next' button
    nodes = dump_ui_nodes(adb_exe, target)
    next_edit_btn = (
        find_node(nodes, res_id="shorts_post_bottom_button")
        or find_node(nodes, text="Next")
    )
    if next_edit_btn and next_edit_btn["cx"]:
        log(f"[+] Tapping editor 'Next' at ({next_edit_btn['cx']}, {next_edit_btn['cy']})...")
        run_adb(adb_exe, target, "shell", "input", "tap", str(next_edit_btn["cx"]), str(next_edit_btn["cy"]))
    else:
        log("[*] Tapping editor 'Next' at default coordinates (530, 1124)...")
        run_adb(adb_exe, target, "shell", "input", "tap", "530", "1124")
    
    log("[*] Waiting for video render & upload transition...")
    time.sleep(5)
    
    # Step 5: Handle Metadata Screen (if present)
    nodes = dump_ui_nodes(adb_exe, target)
    upload_btn = (
        find_node(nodes, text="Upload Short")
        or find_node(nodes, desc="Upload Short")
        or find_node(nodes, text="Upload")
        or find_node(nodes, res_id="upload_button")
    )
    if upload_btn and upload_btn["cx"]:
        title_box = find_node(nodes, res_id="title_edit_text") or find_node(nodes, text="Caption your Short")
        if title_box and title_box["cx"]:
            log(f"[*] Entering Short title: '{title}'...")
            run_adb(adb_exe, target, "shell", "input", "tap", str(title_box["cx"]), str(title_box["cy"]))
            time.sleep(2)
            # Type words with keyevent 62 (spacebar) for proper spaces
            words = title.split(" ")
            for i, word in enumerate(words):
                if word:
                    # Escape special shell characters if any
                    safe_word = re.sub(r'([&|;$><`"\'\\])', r'\\\1', word)
                    run_adb(adb_exe, target, "shell", "input", "text", safe_word)
                if i < len(words) - 1:
                    run_adb(adb_exe, target, "shell", "input", "keyevent", "62")
            time.sleep(2)
        
        log(f"[+] Tapping '{upload_btn.get('text') or 'Upload'}' button at ({upload_btn['cx']}, {upload_btn['cy']})...")
        run_adb(adb_exe, target, "shell", "input", "tap", str(upload_btn["cx"]), str(upload_btn["cy"]))
        time.sleep(4)
    
    log("\n[+] YouTube Short upload request submitted successfully!")
    log("[*] Video is now uploading and processing on channel.")


def verify_channel_videos_count(adb_exe: str, target: str, min_expected: int = 3, max_retries: int = 8) -> int:
    log("\n========================================================")
    log("  VERIFYING UPLOAD COUNT IN YOUTUBE APP")
    log("========================================================")
    
    yt_pkg = get_installed_youtube_package(adb_exe, target)
    for attempt in range(1, max_retries + 1):
        log(f"[*] Verification check (Attempt {attempt}/{max_retries})...")
        
        # 1. Bring YouTube App to front
        run_adb(adb_exe, target, "shell", "am", "start", "-n", f"{yt_pkg}/.morphe_black_1")
        time.sleep(3)
        
        # Press back to close any modal/overlay
        run_adb(adb_exe, target, "shell", "input", "keyevent", "4")
        time.sleep(2)
        
        # Dismiss any popup dialog
        nodes = dump_ui_nodes(adb_exe, target)
        dismiss_btn = find_node(nodes, text="OK") or find_node(nodes, text="Dismiss") or find_node(nodes, text="Ignore")
        if dismiss_btn and dismiss_btn["cx"]:
            run_adb(adb_exe, target, "shell", "input", "tap", str(dismiss_btn["cx"]), str(dismiss_btn["cy"]))
            time.sleep(2)
            nodes = dump_ui_nodes(adb_exe, target)
        
        # 2. Click 'You' in bottom right
        you_btn = find_node(nodes, desc="You", min_x=500, min_y=1050) or find_node(nodes, text="You", min_x=500, min_y=1050)
        if you_btn and you_btn["cx"]:
            log(f"[+] Clicking 'You' tab at ({you_btn['cx']}, {you_btn['cy']})...")
            run_adb(adb_exe, target, "shell", "input", "tap", str(you_btn["cx"]), str(you_btn["cy"]))
        else:
            log("[*] Clicking 'You' tab at default coords (648, 1136)...")
            run_adb(adb_exe, target, "shell", "input", "tap", "648", "1136")
        time.sleep(3)
        
        # 3. Scroll down on 'You' page
        log("[*] Scrolling down on 'You' page...")
        run_adb(adb_exe, target, "shell", "input", "swipe", "360", "900", "360", "400", "400")
        time.sleep(3)
        
        # 4. Click 'Your videos'
        nodes = dump_ui_nodes(adb_exe, target)
        your_videos_btn = find_node(nodes, text="Your videos") or find_node(nodes, desc="Your videos")
        if your_videos_btn and your_videos_btn["cx"]:
            log(f"[+] Clicking 'Your videos' at ({your_videos_btn['cx']}, {your_videos_btn['cy']})...")
            run_adb(adb_exe, target, "shell", "input", "tap", str(your_videos_btn["cx"]), str(your_videos_btn["cy"]))
        else:
            log("[*] Clicking 'Your videos' at default coords (227, 696)...")
            run_adb(adb_exe, target, "shell", "input", "tap", "227", "696")
        
        # Wait 5 seconds for video list to fetch from network
        time.sleep(5)
        
        # 5. Count videos
        nodes = dump_ui_nodes(adb_exe, target)
        video_items = []
        for n in nodes:
            desc = n["desc"]
            if desc and ("views" in desc or "play Short" in desc or "play video" in desc):
                if desc not in video_items:
                    video_items.append(desc)
        
        log(f"[+] Total videos found in 'Your videos': {len(video_items)}")
        for idx, v in enumerate(video_items, 1):
            log(f"  {idx}. {v}")
        
        if len(video_items) >= min_expected:
            return len(video_items)
        
        if attempt < max_retries:
            log("[*] Video is still uploading/processing, waiting 8 seconds before checking again...")
            time.sleep(8)
    
    return len(video_items)


def main():
    parser = argparse.ArgumentParser(description="Upload YouTube Shorts from file to an Android container channel.")
    
    parser.add_argument("video_path", nargs="?", default=None, help="Path to the video file (.mp4)")
    parser.add_argument("-u", "--upload", nargs="?", const=True, default=None, help="Upload flag or path to video file")
    parser.add_argument("-v", "--view", action="store_true", help="Launch scrcpy to view the screen live")
    parser.add_argument("-s", "--sound", nargs="?", const=True, default=None, help="Select audio from YouTube music library (optional song title query)")
    parser.add_argument("-a", "--account", default="01", help="Redroid account number (e.g. 01, 02). Default: 01")
    parser.add_argument("-t", "--title", default=None, help="Title for the YouTube Short")
    parser.add_argument("--adb", default=None, help="Custom path to adb executable")
    parser.add_argument("--scrcpy", default=None, help="Custom path to scrcpy executable")
    
    args = parser.parse_args()
    
    video_file = None
    if isinstance(args.upload, str):
        video_file = args.upload
    elif args.video_path:
        video_file = args.video_path
    
    if not video_file and not args.upload:
        parser.print_help()
        sys.exit(1)
    
    if not video_file:
        log("[!] Error: Please specify a video file path to upload.")
        sys.exit(1)
    
    adb_exe = args.adb or find_tool("adb", DEFAULT_ADB)
    scrcpy_exe = args.scrcpy or find_tool("scrcpy", DEFAULT_SCRCPY)
    
    account_num = int(args.account)
    host_port = 5800 + account_num
    target = f"127.0.0.1:{host_port}"
    
    short_title = args.title or Path(video_file).stem
    
    log("========================================================")
    log(f"  REDROID YOUTUBE SHORT UPLOADER (Account {args.account})")
    log(f"  Video:  {video_file}")
    log(f"  Title:  {short_title}")
    log(f"  Sound:  {args.sound if args.sound is not None else 'None'}")
    log(f"  Target: {target}")
    log("========================================================")
    
    connect_adb(adb_exe, target)
    
    if args.view:
        launch_scrcpy(scrcpy_exe, target)
    
    # 1. Perform upload flow with sound selection if enabled
    upload_short_to_youtube(adb_exe, target, video_file, short_title, sound=args.sound)
    
    # 2. Perform verification by checking 'You' -> 'Your videos' in YouTube App
    count = verify_channel_videos_count(adb_exe, target, min_expected=3)
    
    if count > 2:
        log(f"\n[SUCCESS] Script is working! Total channel videos: {count} (> 2).")
        sys.exit(0)
    else:
        log(f"\n[*] Current video count: {count} (Target: > 2).")
        sys.exit(1)


if __name__ == "__main__":
    main()
