"""
YouTube Short Uploader for Redroid Android Instances
=====================================================
Automates pushing and uploading YouTube Shorts directly from local video files
to the logged-in YouTube channel on a Redroid Android instance.
Supports sound selection, precise audio scrubber timestamp seeking, and multi-account containers.

Usage:
    python upload_short.py -u <video_path> [-v] [--account 01] [--title "Short Title"]
    python upload_short.py <video_path> -u -v -s "Song Name" -t "0:45"

Flags:
    -u, --upload <PATH>      Path to the video file to upload (or standalone flag if path given positionally)
    -v, --view               Launch scrcpy to view the Android screen in real-time
    -a, --account <NUM>      Redroid instance/account number (default: 01 -> port 5801)
    -t, --timestamp <TIME>   Starting timestamp for sound (e.g. '0:30', '1:15', 45, or 'random')
    -s, --sound <TEXT>       Audio track name to search and attach from YouTube music library (optional query)
    -T, --title <TEXT>       Title for the YouTube Short (default: video filename)
"""

import argparse
import os
import sys
import time
import subprocess
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Union, List, Dict, Tuple


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


def parse_timestamp_seconds(ts_str: str) -> float:
    """Parses timestamp strings like '1:30', '0:45', '45s', '45' into seconds."""
    ts_str = str(ts_str).strip().lower().rstrip('s')
    if ":" in ts_str:
        parts = ts_str.split(":")
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return float(ts_str)


def input_fast_text(adb_exe: str, target: str, text: str):
    """Enters text with spaces in one single ADB command using %s escaping."""
    safe_text = text.replace(" ", "%s")
    safe_text = re.sub(r'([&|;$><`"\'\\])', r'\\\1', safe_text)
    run_adb(adb_exe, target, "shell", "input", "text", safe_text)


def upload_short_to_youtube(adb_exe: str, target: str, video_path: str, title: str, sound: Optional[str] = None, timestamp: Optional[str] = None):
    log("\n========================================================")
    log("  AUTOMATING YOUTUBE SHORT UPLOAD (FAST MODE)")
    log("========================================================")
    
    yt_pkg = get_installed_youtube_package(adb_exe, target)
    
    # Step 1: Push and index video
    content_uri = push_and_index_video(adb_exe, target, video_path)
    
    # Step 2: Reset YouTube and launch direct video upload intent
    log(f"[*] Launching YouTube Short upload editor ({yt_pkg})...")
    run_adb(adb_exe, target, "shell", "am", "force-stop", yt_pkg)
    time.sleep(1.5)
    
    upload_cmd = [
        "am", "start",
        "-n", f"{yt_pkg}/com.google.android.apps.youtube.app.application.Shell_UploadActivity",
        "-d", content_uri,
        "-a", "android.intent.action.SEND",
        "-t", "video/mp4",
        "--eu", "android.intent.extra.STREAM", content_uri
    ]
    run_adb(adb_exe, target, "shell", *upload_cmd)
    log("[*] Video trimmer loading...")
    time.sleep(3)
    
    # Step 3: Handle Trimmer Screen -> Tap 'Next' at (627, 1112)
    log("[+] Tapping trimmer 'Next'...")
    run_adb(adb_exe, target, "shell", "input", "tap", "627", "1112")
    time.sleep(3)
    
    # Step 4: Handle Shorts Editor Screen
    log("[*] Navigating Shorts editor...")
    
    # Check if sound selection was requested via -s / --sound flag
    if sound:
        log("[*] Sound flag detected: Selecting audio track from YouTube music library...")
        # Tap 'Add sound' button
        run_adb(adb_exe, target, "shell", "input", "tap", "360", "120")
        time.sleep(2)
        
        # If a specific song query was passed as string (e.g. --sound "Sunflower")
        if isinstance(sound, str) and sound.strip() and sound.strip().lower() not in ("true", "1"):
            search_query = sound.strip()
            log(f"[*] Searching for audio track '{search_query}'...")
            run_adb(adb_exe, target, "shell", "input", "tap", "360", "212")
            time.sleep(0.8)
            input_fast_text(adb_exe, target, search_query)
            run_adb(adb_exe, target, "shell", "input", "keyevent", "66")
            time.sleep(2.5)
            
            # Tap first search result track at (360, 470)
            log("[*] Selecting search result track...")
            run_adb(adb_exe, target, "shell", "input", "tap", "360", "470")
            time.sleep(1.5)
        else:
            # Tap first recommended track at (300, 460)
            log("[*] Selecting top track from music library...")
            run_adb(adb_exe, target, "shell", "input", "tap", "300", "460")
            time.sleep(1.5)
        
        # Tap 'Add this music to your video' button at (648, 460)
        log("[+] Attaching selected music...")
        run_adb(adb_exe, target, "shell", "input", "tap", "648", "460")
        time.sleep(2)
        log("[+] Sound successfully attached to Short!")
        
        # Check if timestamp adjustment was requested via -t / --timestamp
        if timestamp:
            log(f"[*] Adjusting audio starting timestamp ('{timestamp}')...")
            # Tap sound capsule in editor to open "Adjust sound" modal
            run_adb(adb_exe, target, "shell", "input", "tap", "360", "120")
            time.sleep(2)
            
            # Read exact song duration from audio adjust modal
            nodes = dump_ui_nodes(adb_exe, target)
            dur_node = find_node(nodes, res_id="audio_duration_text")
            seekbar_node = find_node(nodes, res_id="play_progress_bar")
            
            total_duration_sec = 158.0 # default fallback
            if dur_node and dur_node["text"]:
                try:
                    total_duration_sec = parse_timestamp_seconds(dur_node["text"])
                except Exception:
                    pass
            elif seekbar_node and seekbar_node["desc"]:
                m = re.search(r"out of (?:(\d+) minutes? )?(?:(\d+) seconds?)?", seekbar_node["desc"])
                if m:
                    mins = int(m.group(1)) if m.group(1) else 0
                    secs = int(m.group(2)) if m.group(2) else 0
                    if mins or secs:
                        total_duration_sec = float(mins * 60 + secs)
            
            if str(timestamp).strip().lower() in ("random", "rand", "true"):
                import random
                max_start = max(5.0, total_duration_sec - 15.0)
                target_sec = random.uniform(5.0, max_start)
                log(f"[+] Selected random timestamp: {int(target_sec//60)}:{int(target_sec%60):02d} ({target_sec:.1f}s / {total_duration_sec:.1f}s)")
            else:
                target_sec = parse_timestamp_seconds(str(timestamp))
                log(f"[+] Target audio timestamp: {int(target_sec//60)}:{int(target_sec%60):02d} ({target_sec:.1f}s / {total_duration_sec:.1f}s)")
            
            # Stage 1: Coarse seek on seekbar (x=96 to x=624, width=528)
            track_left = 96
            track_right = 624
            usable_width = track_right - track_left
            
            ratio = min(1.0, max(0.0, target_sec / max(1.0, total_duration_sec)))
            tap_x = int(track_left + ratio * usable_width)
            log(f"[*] Coarse seek to position on scrubber at ({tap_x}, 832)...")
            run_adb(adb_exe, target, "shell", "input", "tap", str(tap_x), "832")
            time.sleep(1.2)
            
            # Stage 2: Precision continuous micro-adjustment on waveform (y=960, ~100px per second)
            for step in range(5):
                nodes = dump_ui_nodes(adb_exe, target)
                pos_node = find_node(nodes, res_id="play_position_text")
                curr_sec = parse_timestamp_seconds(pos_node["text"]) if pos_node and pos_node["text"] else target_sec
                diff_sec = target_sec - curr_sec
                
                if abs(diff_sec) < 0.5:
                    log(f"[+] Exact target timestamp reached: {pos_node['text']} ({curr_sec:.1f}s)!")
                    break
                
                swipe_dx = int(diff_sec * 100)
                swipe_dx = max(-350, min(350, swipe_dx))
                start_x = 360
                end_x = start_x - swipe_dx
                log(f"[*] Micro-adjusting waveform ({pos_node.get('text', '')} -> target, diff {diff_sec:+.1f}s)...")
                run_adb(adb_exe, target, "shell", "input", "swipe", str(start_x), "960", str(end_x), "960", "250")
                time.sleep(1.0)
            
            # Tap 'Done' button at (632, 1112)
            run_adb(adb_exe, target, "shell", "input", "tap", "632", "1112")
            time.sleep(1.5)
            log("[+] Audio timestamp adjusted and applied successfully!")
    
    # Tap editor 'Next' button at (530, 1124)
    log("[+] Tapping editor 'Next'...")
    run_adb(adb_exe, target, "shell", "input", "tap", "530", "1124")
    log("[*] Waiting for video render & metadata screen...")
    time.sleep(4)
    
    # Step 5: Handle Metadata Screen
    log("[*] Navigating metadata screen...")
    log(f"[*] Entering Short title: '{title}'...")
    # Tap title box
    run_adb(adb_exe, target, "shell", "input", "tap", "360", "240")
    time.sleep(1.5)
    input_fast_text(adb_exe, target, title)
    time.sleep(1.5)
    
    # Dismiss soft keyboard using KEYCODE_BACK (4) so screen returns to full height
    log("[*] Dismissing soft keyboard...")
    run_adb(adb_exe, target, "shell", "input", "keyevent", "4")
    time.sleep(2)
    
    # Tap 'Upload Short' button at bottom (360, 1120)
    log("[+] Tapping 'Upload Short' button at (360, 1120)...")
    run_adb(adb_exe, target, "shell", "input", "tap", "360", "1120")
    time.sleep(3)
    
    log("\n[+] YouTube Short upload request submitted successfully!")
    log("[*] Video is now uploading and processing on channel.")


def main():
    parser = argparse.ArgumentParser(description="Upload YouTube Shorts from file to an Android container channel.")
    
    parser.add_argument("video_path", nargs="?", default=None, help="Path to the video file (.mp4)")
    parser.add_argument("-u", "--upload", nargs="?", const=True, default=None, help="Upload flag or path to video file")
    parser.add_argument("-v", "--view", action="store_true", help="Launch scrcpy to view the screen live")
    parser.add_argument("-s", "--sound", nargs="?", const=True, default=None, help="Select audio from YouTube music library (optional song title query)")
    parser.add_argument("-t", "--timestamp", nargs="?", const="random", default=None, help="Starting timestamp for sound (e.g. -t '0:30', -t '1:15', -t 45, or -t / -t random)")
    parser.add_argument("-a", "--account", default="01", help="Redroid account number (e.g. 01, 02). Default: 01")
    parser.add_argument("--title", "-T", default=None, help="Title for the YouTube Short")
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
    
    sound_arg = args.sound
    if args.timestamp and sound_arg is None:
        sound_arg = True
    
    log("========================================================")
    log(f"  REDROID YOUTUBE SHORT UPLOADER (Account {args.account})")
    log(f"  Video:     {video_file}")
    log(f"  Title:     {short_title}")
    log(f"  Sound:     {sound_arg if sound_arg is not None else 'None'}")
    log(f"  Timestamp: {args.timestamp if args.timestamp is not None else 'Default'}")
    log(f"  Target:    {target}")
    log("========================================================")
    
    connect_adb(adb_exe, target)
    
    if args.view:
        launch_scrcpy(scrcpy_exe, target)
    
    # Perform upload flow with sound and audio timestamp if enabled
    upload_short_to_youtube(adb_exe, target, video_file, short_title, sound=sound_arg, timestamp=args.timestamp)
    
    log(f"\n[SUCCESS] YouTube Short '{short_title}' uploaded successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main()
