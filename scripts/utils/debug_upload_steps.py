import subprocess
import time
import os
import re

adb = r"C:\Users\Shahid\tools\scrcpy\adb.exe"
target = "127.0.0.1:5555"
yt_pkg = "app.revanced.android.youtube"

os.makedirs("debug/steps", exist_ok=True)

def screenshot(name: str):
    path = f"debug/steps/{name}.png"
    subprocess.run([adb, "-s", target, "exec-out", "screencap", "-p"], stdout=open(path, "wb"))
    print(f"[+] Saved screenshot: {path}")

def tap(x: int, y: int, delay: float = 2.0):
    print(f"[*] Tapping ({x}, {y})...")
    subprocess.run([adb, "-s", target, "shell", "input", "tap", str(x), str(y)])
    time.sleep(delay)

def get_focus():
    res = subprocess.run([adb, "-s", target, "shell", "dumpsys window | grep -E mCurrentFocus"], capture_output=True, text=True).stdout.strip()
    print(f"[*] Focus: {res}")
    return res

def run_debug():
    video_file = r"upload files\Piracy On Next Level_ What Is FHMY_.mp4"
    if not os.path.exists(video_file):
        video_file = r"downloads\test_short.mp4"
        
    print(f"[*] Target Video: {video_file}")
    
    # Step 1: Push video & Scan
    rem_path = f"/sdcard/DCIM/Camera/debug_short_{int(time.time())}.mp4"
    print(f"[*] Step 1: Pushing video -> {rem_path}...")
    subprocess.run([adb, "-s", target, "push", video_file, rem_path], check=True)
    subprocess.run([adb, "-s", target, "shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{rem_path}"])
    time.sleep(2)
    
    # Query exact URI
    q_res = subprocess.run([adb, "-s", target, "shell", "content query --uri content://media/external/video/media --projection _id:_data"], capture_output=True, text=True).stdout
    ids = re.findall(r"_id=(\d+)", q_res)
    uri = f"content://media/external/video/media/{ids[-1]}"
    print(f"[*] Resolved MediaStore URI: {uri}")
    
    # Step 2: Launch Upload Activity
    print("[*] Step 2: Force stopping YouTube & Launching UploadActivity...")
    subprocess.run([adb, "-s", target, "shell", "am", "force-stop", yt_pkg])
    time.sleep(1)
    
    subprocess.run([adb, "-s", target, "shell", "am", "start",
                    "-n", f"{yt_pkg}/com.google.android.apps.youtube.app.application.Shell_UploadActivity",
                    "-d", uri,
                    "-a", "android.intent.action.SEND",
                    "-t", "video/mp4",
                    "--eu", "android.intent.extra.STREAM", uri], check=True)
    time.sleep(4)
    get_focus()
    screenshot("01_initial_launch")
    
    # Step 3: Check "Add sound" button
    print("[*] Step 3: Tapping 'Add sound' at (360, 80)...")
    tap(360, 80, delay=3.0)
    get_focus()
    screenshot("02_add_sound_screen")
    
    # Step 4: Search for sound "sunflower"
    print("[*] Step 4: Tapping Search icon at (660, 80)...")
    tap(660, 80, delay=1.5)
    screenshot("03_search_opened")
    
    print("[*] Typing search query: sunflower...")
    subprocess.run([adb, "-s", target, "shell", "input", "text", "sunflower"])
    time.sleep(1)
    subprocess.run([adb, "-s", target, "shell", "input", "keyevent", "66"]) # Enter
    time.sleep(3)
    screenshot("04_search_results")
    
    # Step 5: Select top track
    print("[*] Step 5: Tapping top track in search results at (360, 260)...")
    tap(360, 260, delay=2.0)
    screenshot("05_track_selected_preview")
    
    # Step 6: Click blue use sound button (arrow)
    print("[*] Step 6: Tapping blue 'Use this sound' button at (640, 260)...")
    tap(640, 260, delay=3.5)
    screenshot("06_sound_attached_preview")
    
    # Step 7: Click Next / Checkmark button
    print("[*] Step 7: Tapping 'Next' on editor screen at (640, 1220)...")
    tap(640, 1220, delay=3.5)
    get_focus()
    screenshot("07_details_screen")
    
    # Step 8: Enter Title
    print("[*] Step 8: Tapping Caption/Title box at (250, 360)...")
    tap(250, 360, delay=1.0)
    screenshot("08_title_focused")
    
    title_text = "Piracy On Next Level"
    safe_text = title_text.replace(" ", "%s")
    subprocess.run([adb, "-s", target, "shell", "input", "text", safe_text])
    time.sleep(1)
    # Hide keyboard
    subprocess.run([adb, "-s", target, "shell", "input", "keyevent", "111"]) # ESC
    time.sleep(1.5)
    screenshot("09_title_entered")
    
    # Step 9: Click Upload Short
    print("[*] Step 9: Tapping 'Upload Short' at (360, 1220)...")
    tap(360, 1220, delay=4.0)
    get_focus()
    screenshot("10_upload_submitted")
    
    # Step 10: Check Library / Channel
    print("[*] Step 10: Navigating to You -> Your videos...")
    tap(640, 1230, delay=2.5) # You tab
    screenshot("11_you_tab")
    
    tap(250, 480, delay=3.0) # Your videos
    screenshot("12_your_videos_list")
    
    print("[+] Diagnostic step-by-step execution finished!")

if __name__ == "__main__":
    run_debug()
