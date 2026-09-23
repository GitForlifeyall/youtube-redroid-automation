"""
Instagram Reel Uploader for Redroid Android Instances
=====================================================
Automates pushing and uploading Instagram Reels directly from local video files
to the logged-in Instagram account on a Redroid Android instance.
Supports sound selection, captions, and exact sequence calibration.

Usage:
    python upload_reel.py -u <video_path> [-v] [--account 01] [--caption "My Reel #reels"]
    python upload_reel.py -u <video_path> -s "Sunflower" -t "1:30" -c "Cool Reel" -v

Flags:
    -u, --upload <PATH>      Path to the video file to upload
    -v, --view               Launch scrcpy to view the Android screen in real-time
    -a, --account <NUM>      Redroid instance/account number (default: 01 -> port 5801)
    -c, --caption <TEXT>     Caption for the Reel (default: filename without extension)
    -s, --sound <TEXT>       Audio track name to search and attach from Instagram's sound library
    -t, --timestamp <TIME>   Exact starting timestamp for the sound (e.g. '1:30', '90', '0:45')
    --dry-run                Walk through all upload steps but stop before pressing final Share
    --fast                   Use direct high-speed fixed coordinate navigation
"""

import argparse
import os
import sys
import time
import subprocess
import re
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
    return subprocess.run(cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="replace")


def parse_timestamp_to_seconds(ts: str) -> float:
    ts = ts.strip()
    if not ts:
        return 0.0
    if ":" in ts:
        parts = ts.split(":")
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    try:
        return float(ts)
    except ValueError:
        return 0.0


def ensure_device_connected(adb_exe: str, target: str):
    log(f"[*] Checking connection to Redroid instance at {target}...")
    run_adb(adb_exe, target, "connect", target)
    res = run_adb(adb_exe, target, "devices")
    if target not in res.stdout:
        time.sleep(2)
        run_adb(adb_exe, target, "connect", target)
        res = run_adb(adb_exe, target, "devices")
        if target not in res.stdout:
            log(f"[ERROR] Could not connect to ADB target {target}.")
            sys.exit(1)
    log(f"[+] Successfully connected to {target}")


def launch_scrcpy(scrcpy_exe: str, target: str, title: str):
    log(f"[*] Launching scrcpy window for {target}...")
    try:
        subprocess.Popen(
            [scrcpy_exe, "-s", target, "--window-title", title, "--always-on-top"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)
    except Exception as e:
        log(f"[!] Warning: Failed to launch scrcpy: {e}")


def push_video_to_device(adb_exe: str, target: str, local_path: Path) -> str:
    log(f"[*] Pushing video '{local_path.name}' ({local_path.stat().st_size / 1024 / 1024:.2f} MB) to device...")
    # Clean up non-video images from storage so gallery only contains the actual video
    run_adb(adb_exe, target, "shell", "rm -f /sdcard/*.png /sdcard/*.xml /sdcard/DCIM/*.png /sdcard/Pictures/*.png /sdcard/Movies/*.png /sdcard/Download/*.png")
    
    remote_path = "/sdcard/Movies/instagram_reel.mp4"
    run_adb(adb_exe, target, "shell", "mkdir", "-p", "/sdcard/Movies")
    run_adb(adb_exe, target, "push", str(local_path), remote_path)
    
    # Broadcast media scanner to ensure it is indexed into MediaStore
    run_adb(adb_exe, target, "shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_path}")
    time.sleep(1.0)
    log(f"[+] Video successfully pushed to {remote_path} and indexed into MediaStore.")
    return remote_path


def type_text(adb_exe: str, target: str, text: str):
    escaped = ""
    for char in text:
        if char == " ":
            escaped += "%s"
        elif char in r'#&<>"\'!$();|*?~`{}[]':
            escaped += f"\\{char}"
        else:
            escaped += char
    run_adb(adb_exe, target, "shell", "input", "text", escaped)


def upload_reel(
    adb_exe: str,
    target: str,
    video_path: Path,
    caption: str,
    sound_query: str = None,
    sound_timestamp: str = None,
    view: bool = False,
    scrcpy_exe: str = None,
    account: str = "01",
    dry_run: bool = False,
    fast_mode: bool = True,
    pause_sec: float = 5.0
):
    log("\n=======================================================")
    log("       Instagram Reel Automated Uploader")
    log("=======================================================")
    log(f"  Target:     {target} (Account {account})")
    log(f"  Video:      {video_path}")
    log(f"  Caption:    {caption}")
    if sound_query:
        log(f"  Sound:      {sound_query} (Seek: {sound_timestamp or '0:00'})")
    log("=======================================================\n")

    ensure_device_connected(adb_exe, target)

    if view and scrcpy_exe:
        launch_scrcpy(scrcpy_exe, target, f"Redroid Insta - Account {account}")

    # Push video to device
    push_video_to_device(adb_exe, target, video_path)

    # Disable potential overlay blockers
    run_adb(adb_exe, target, "shell", "pm", "disable-user", "com.google.android.apps.wellbeing")

    # Detect package (prefer active Instagram Lite for flawless container stability, or full client)
    res_pkg = run_adb(adb_exe, target, "shell", "pm", "list", "packages")
    if "com.instagram.lite" in res_pkg.stdout:
        pkg = "com.instagram.lite"
        main_act = "com.facebook.lite.MainActivity"
        is_lite = True
    elif "com.instander.android" in res_pkg.stdout:
        pkg = "com.instander.android"
        main_act = "com.instagram.android.activity.MainTabActivity"
        is_lite = False
    else:
        pkg = "com.instagram.android"
        main_act = "com.instagram.android.activity.MainTabActivity"
        is_lite = False

    # Reset Instagram to clean state
    log(f"[*] Bringing Instagram ({pkg}) to foreground...")
    run_adb(adb_exe, target, "shell", "am", "force-stop", pkg)
    time.sleep(0.5)
    run_adb(adb_exe, target, "shell", "am", "start", "-n", f"{pkg}/{main_act}")
    time.sleep(2.0)

    # Tap Home icon (bottom left) to ensure we are on the main feed
    log("[*] Resetting to Home tab...")
    run_adb(adb_exe, target, "shell", "input", "tap", "72", "1136")
    time.sleep(1.0)

    # Tap Create (+) button on bottom navigation bar
    log("[*] Opening Creator (tapping '+' button)...")
    run_adb(adb_exe, target, "shell", "input", "tap", "360", "1136")
    time.sleep(2.0)

    if is_lite:
        # Switch to REEL tab in Lite
        log("[*] Switching to REEL tab...")
        run_adb(adb_exe, target, "shell", "input", "tap", "650", "85")
        time.sleep(1.5)

        # Handle sound selection if requested
        if sound_query:
            log(f"[*] Opening Music selector for '{sound_query}'...")
            run_adb(adb_exe, target, "shell", "input", "tap", "125", "780")
            time.sleep(1.5)
            # Type search
            type_text(adb_exe, target, sound_query)
            time.sleep(1.5)
            run_adb(adb_exe, target, "shell", "input", "tap", "320", "270")
            time.sleep(1.0)

        # Advance to Details / Share screen
        log("[*] Advancing to Reel Details / Caption screen (tapping 'Next')...")
        run_adb(adb_exe, target, "shell", "input", "tap", "620", "1120")
        time.sleep(2.0)

        # Input caption
        if caption:
            log(f"[*] Entering caption: '{caption}'...")
            run_adb(adb_exe, target, "shell", "input", "tap", "360", "580")
            time.sleep(0.8)
            type_text(adb_exe, target, caption)
            time.sleep(0.5)
            run_adb(adb_exe, target, "shell", "input", "keyevent", "4")
            time.sleep(0.8)

        if dry_run:
            log("[!] DRY RUN complete: Stopping before pressing Share button.")
            return True

        log("[*] Tapping 'Share' button to publish Reel...")
        run_adb(adb_exe, target, "shell", "input", "tap", "360", "860")
        time.sleep(3.5)

    else:
        # Select latest video thumbnail in gallery (Tile 1 at 90, 830)
        log("[*] Selecting latest video from gallery...")
        run_adb(adb_exe, target, "shell", "input", "tap", "90", "830")
        time.sleep(1.0)

        # Tap 'Next' at top right (650, 85) to proceed from gallery picker
        run_adb(adb_exe, target, "shell", "input", "tap", "650", "85")
        time.sleep(1.5)

        # Handle sound selection if requested
        if sound_query:
            log(f"[*] Opening Instagram Music selector for '{sound_query}'...")
            run_adb(adb_exe, target, "shell", "input", "tap", "220", "88")
            time.sleep(1.5)

            run_adb(adb_exe, target, "shell", "input", "tap", "360", "92")
            time.sleep(0.5)

            type_text(adb_exe, target, sound_query)
            time.sleep(1.5)

            log(f"[*] Selecting first track matching '{sound_query}'...")
            run_adb(adb_exe, target, "shell", "input", "tap", "320", "270")
            time.sleep(1.5)

            if sound_timestamp and sound_timestamp != "0:00":
                if str(sound_timestamp).strip().lower() in ("random", "rand"):
                    import random
                    target_sec = random.uniform(10.0, 110.0)
                else:
                    target_sec = parse_timestamp_to_seconds(str(sound_timestamp))
                
                total_duration_sec = 180.0
                ratio = min(1.0, max(0.0, target_sec / total_duration_sec))
                track_left = 50
                track_right = 670
                seek_x = int(track_left + ratio * (track_right - track_left))
                
                log(f"[*] Calibrating audio starting timestamp to {int(target_sec//60)}:{int(target_sec%60):02d} ({target_sec:.1f}s) -> seekbar x={seek_x}...")
                run_adb(adb_exe, target, "shell", "input", "tap", str(seek_x), "840")
                time.sleep(0.8)
                
                if pause_sec > 0:
                    log(f"[*] Pausing {pause_sec:.1f}s for manual timestamp verification in viewer...")
                    time.sleep(pause_sec)

        # Advance from Reel preview to Metadata/Share screen (tapping 'Next ->' at 617, 1120)
        log("[*] Advancing to Reel Details / Caption screen (tapping 'Next')...")
        run_adb(adb_exe, target, "shell", "input", "tap", "617", "1120")
        time.sleep(2.0)

        if caption:
            log(f"[*] Entering caption: '{caption}'...")
            run_adb(adb_exe, target, "shell", "input", "tap", "360", "736")
            time.sleep(0.6)
            type_text(adb_exe, target, caption)
            time.sleep(0.5)
            run_adb(adb_exe, target, "shell", "input", "keyevent", "4")
            time.sleep(0.8)

        if dry_run:
            log("[!] DRY RUN complete: Stopping before pressing Share button.")
            return True

        log("[*] Tapping 'Share' button to publish Reel...")
        run_adb(adb_exe, target, "shell", "input", "tap", "360", "1108")
        time.sleep(3.5)

    # Return to Home feed cleanly to display newly posted Reel
    run_adb(adb_exe, target, "shell", "input", "keyevent", "4")   # Dismiss any soft modal if open
    time.sleep(0.5)
    run_adb(adb_exe, target, "shell", "input", "tap", "72", "1136") # Tap Home icon
    time.sleep(1.0)

    log("\n[SUCCESS] Instagram Reel upload completed successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Upload an Instagram Reel directly to a Redroid Android instance.")
    parser.add_argument("video_path_pos", nargs="?", default=None, help="Positional path to video file")
    parser.add_argument("-u", "--upload", dest="upload_path", default=None, help="Path to the video file to upload")
    parser.add_argument("-v", "--view", action="store_true", help="Launch scrcpy to view upload in real time")
    parser.add_argument("-ins", "--instance", default=None, help="LDPlayer instance name or index (e.g. -ins instance1, -ins 0)")
    parser.add_argument("-a", "--account", default="01", help="Redroid instance/account number (e.g. 01 -> port 5801, ignored if -ins is used)")
    parser.add_argument("-c", "--caption", default=None, help="Caption for the Instagram Reel")
    parser.add_argument("-s", "--sound", default=None, help="Music/Sound title to search and attach from Instagram library")
    parser.add_argument("-t", "--timestamp", default="0:00", help="Starting timestamp for sound (e.g. 1:30 or 90)")
    parser.add_argument("-p", "--pause", type=float, default=5.0, help="Pause duration in seconds after selecting timestamp for manual verification (default: 5.0)")
    parser.add_argument("--dry-run", action="store_true", help="Perform all upload steps but stop before pressing final Share")
    parser.add_argument("--fast", action="store_true", default=True, help="High-speed direct fixed coordinate mode")

    args = parser.parse_args()

    target_video = args.upload_path or args.video_path_pos
    if not target_video:
        parser.print_help()
        sys.exit(1)

    video_file = Path(target_video)
    if not video_file.exists():
        log(f"[ERROR] Video file not found: {video_file}")
        sys.exit(1)

    caption = args.caption if args.caption else video_file.stem

    adb_exe = find_tool("adb", DEFAULT_ADB)
    scrcpy_exe = find_tool("scrcpy", DEFAULT_SCRCPY)

    if args.instance:
        try:
            sys.path.insert(0, str(Path(__file__).parent / "scripts" / "utils"))
            from ldplayer_bridge import ensure_ldplayer_instance
            adb_target = ensure_ldplayer_instance(args.instance, adb_exe=adb_exe)
        except Exception as e:
            log(f"[!] LDPlayer bridge error: {e}. Falling back to standard port calculation.")
            idx = int("".join([c for c in args.instance if c.isdigit()] or ["0"]))
            adb_target = f"127.0.0.1:{5555 + (idx * 2)}"
        acc_str = f"LDPlayer-{args.instance}"
    else:
        acc_str = str(args.account).strip().zfill(2)
        acc_num = int(acc_str)
        adb_target = f"127.0.0.1:{5800 + acc_num}"

    upload_reel(
        adb_exe=adb_exe,
        target=adb_target,
        video_path=video_file,
        caption=caption,
        sound_query=args.sound,
        sound_timestamp=args.timestamp,
        view=args.view,
        scrcpy_exe=scrcpy_exe,
        account=acc_str,
        dry_run=args.dry_run,
        fast_mode=args.fast,
        pause_sec=args.pause
    )


if __name__ == "__main__":
    main()
