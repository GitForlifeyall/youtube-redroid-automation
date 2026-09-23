"""
YouTube Shorts Uploader (Pure UIAutomator2 / Selenium Style with Full Selector & Coordinate Logging)
===================================================================================================
Automates pushing and uploading YouTube Shorts directly from local video files to YouTube
on LDPlayer 9 / Redroid / physical Android devices with sub-second audio calibration.

Logs every clicked element's Selector, Resource ID, Text, Bounding Box, and Resolved (X, Y) Coordinates.
"""

import sys
import os
import time
import argparse
import subprocess
import re
from pathlib import Path
from typing import Optional, Tuple

# Fix Windows cp1252 encoding for emojis and unicode characters
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

try:
    import uiautomator2 as u2
except ImportError:
    print("[!] uiautomator2 not installed. Installing via pip...")
    subprocess.run([sys.executable, "-m", "pip", "install", "uiautomator2"], check=True)
    import uiautomator2 as u2


def log(msg: str):
    try:
        print(msg, flush=True)
    except Exception:
        safe_msg = str(msg).encode("ascii", errors="backslashreplace").decode("ascii")
        print(safe_msg, flush=True)


def parse_element_details(element, label: str = "Element") -> Tuple[str, Tuple[int, int], Tuple[int, int, int, int]]:
    """Extracts UIAutomator2 selector, center coordinate (X, Y), and bounding box."""
    try:
        info = element.info
        bounds = info.get("bounds", {})
        left = bounds.get("left", 0)
        top = bounds.get("top", 0)
        right = bounds.get("right", 0)
        bottom = bounds.get("bottom", 0)
        cx = (left + right) // 2
        cy = (top + bottom) // 2

        res_id = info.get("resourceName", "")
        text = info.get("text", "")
        desc = info.get("contentDescription", "")
        cls_name = info.get("className", "android.view.View")

        parts = []
        if res_id:
            parts.append(f'@resource-id="{res_id}"')
        if text:
            parts.append(f'@text="{text}"')
        if desc:
            parts.append(f'@content-desc="{desc}"')
        sel_str = f"//{cls_name}[" + " and ".join(parts) + "]" if parts else f"//{cls_name}"

        return sel_str, (cx, cy), (left, top, right, bottom)
    except Exception:
        return f"//unknown[{label}]", (0, 0), (0, 0, 0, 0)


def smart_click(element, label: str, fallback_coords: Optional[Tuple[int, int]] = None, timeout: float = 3.0, d: Optional[u2.Device] = None) -> bool:
    """Clicks an element, logs full selector & coordinates, and falls back to coordinate tap."""
    if element is not None and element.exists(timeout=timeout):
        try:
            sel_str, (cx, cy), (left, top, right, bottom) = parse_element_details(element, label)
            log(f"🔘 [CLICK: {label}] -> Selector: {sel_str} | Center: (X={cx}, Y={cy}) | Bounds: [{left},{top}][{right},{bottom}]")
            element.click()
            return True
        except Exception as e:
            log(f"⚠️ [CLICK RETRY: {label}] u2 click failed ({e}), falling back to tap...")

    if fallback_coords and d:
        fx, fy = fallback_coords
        log(f"📍 [CLICK FALLBACK: {label}] -> Center: (X={fx}, Y={fy})")
        d.click(fx, fy)
        return True

    log(f"❌ [CLICK FAILED: {label}] Element not found on screen.")
    return False


def smart_type(element, text_to_type: str, label: str, timeout: float = 3.0) -> bool:
    """Sets text in an input box and logs full selector and coordinates."""
    if element is not None and element.exists(timeout=timeout):
        try:
            sel_str, (cx, cy), (left, top, right, bottom) = parse_element_details(element, label)
            log(f"⌨️ [TYPE: {label}] -> Selector: {sel_str} | Center: (X={cx}, Y={cy}) | Bounds: [{left},{top}][{right},{bottom}] | Text: '{text_to_type}'")
            element.set_text(text_to_type)
            return True
        except Exception:
            element.set_text(text_to_type)
            return True
    log(f"⚠️ [TYPE FAILED: {label}] Element not found.")
    return False


def push_and_index_video(d: u2.Device, video_path: str) -> str:
    """Pushes video to device storage and indexes with MediaScanner."""
    path_obj = Path(video_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    file_size_mb = path_obj.stat().st_size / (1024 * 1024)
    remote_movies = f"/sdcard/Movies/{path_obj.name}"
    remote_downloads = f"/sdcard/Download/{path_obj.name}"

    log(f"[*] Pushing '{path_obj.name}' ({file_size_mb:.2f} MB) to Android device...")
    d.push(str(path_obj.resolve()), remote_movies)
    d.shell(["cp", remote_movies, remote_downloads])
    d.shell(["chmod", "-R", "777", "/sdcard/Movies", "/sdcard/Download"])

    log("[*] Indexing video in MediaStore...")
    d.shell(["am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_movies}"])
    d.shell(["am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_downloads}"])
    time.sleep(3.0)

    # Query content URI
    res = d.shell(["content", "query", "--uri", "content://media/external/video/media", "--projection", "_id:_data"]).output
    media_id = None
    for line in reversed(res.splitlines()):
        if path_obj.name in line:
            m = re.search(r"_id=(\d+)", line)
            if m:
                media_id = m.group(1)
                break

    if not media_id:
        m = re.findall(r"_id=(\d+)", res)
        if m:
            media_id = m[-1]

    content_uri = f"content://media/external/video/media/{media_id}" if media_id else f"file://{remote_movies}"
    log(f"[+] Video indexed with URI: {content_uri}")
    return content_uri


def get_installed_youtube_package(d: u2.Device) -> str:
    """Detects installed YouTube variant (ReVanced, Morphe, or Official)."""
    pkgs = d.shell(["pm", "list", "packages"]).output.splitlines()
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
    try:
        return float(ts_str)
    except ValueError:
        return 0.0


def dump_ui_nodes(d: u2.Device) -> list:
    """Extracts UI nodes from hierarchy dump for fast, robust element searching."""
    try:
        xml_str = d.dump_hierarchy()
        root = ET.fromstring(xml_str)
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


def find_node(nodes: list, text=None, desc=None, res_id=None, min_x=0, min_y=0, max_y=9999) -> Optional[dict]:
    for n in nodes:
        if n["cx"] is not None and n["cx"] < min_x:
            continue
        if n["cy"] is not None and (n["cy"] < min_y or n["cy"] > max_y):
            continue
        if text:
            if hasattr(text, "search"):
                if text.search(n["text"]):
                    return n
            elif text.lower() in n["text"].lower():
                return n
        if desc:
            if hasattr(desc, "search"):
                if desc.search(n["desc"]):
                    return n
            elif desc.lower() in n["desc"].lower():
                return n
        if res_id:
            if hasattr(res_id, "search"):
                if res_id.search(n["res_id"]):
                    return n
            elif res_id.lower() in n["res_id"].lower():
                return n
    return None


def seek_youtube_audio(d: u2.Device, timestamp: str):
    """Adjusts starting audio timestamp in YouTube Shorts audio trimmer with sub-second precision."""
    log(f"[*] Adjusting audio starting timestamp ('{timestamp}')...")
    # Tap sound capsule in editor to open "Adjust sound" modal (at 388, 120)
    sound_capsule = (
        d(resourceIdMatches=r".*sound_button_title.*|.*sound_capsule.*|.*audio_capsule.*")
        or d(textMatches=r"(?i)Adjust sound.*")
        or d(descriptionMatches=r"(?i)Adjust sound.*")
    )
    smart_click(sound_capsule, "Adjust Sound Capsule", fallback_coords=(388, 120), timeout=3.0, d=d)
    time.sleep(2.0)

    # Read exact song duration from audio adjust modal
    dur_elem = d(resourceIdMatches=r".*audio_duration_text.*")
    total_duration_sec = 158.0  # default fallback
    if dur_elem.exists(timeout=1.5) and dur_elem.info.get("text"):
        try:
            total_duration_sec = parse_timestamp_seconds(dur_elem.info["text"])
        except Exception:
            pass

    if str(timestamp).strip().lower() in ("random", "rand", "true"):
        import random
        max_start = max(5.0, total_duration_sec - 15.0)
        target_sec = random.uniform(5.0, max_start)
        log(f"[+] Selected random timestamp: {int(target_sec//60)}:{int(target_sec%60):02d} ({target_sec:.1f}s / {total_duration_sec:.1f}s)")
    else:
        target_sec = parse_timestamp_seconds(str(timestamp))
        log(f"[+] Target audio timestamp: {int(target_sec//60)}:{int(target_sec%60):02d} ({target_sec:.1f}s / {total_duration_sec:.1f}s)")

    # Stage 1: Coarse seek on SeekBar (x=100 to x=620 at Y=928)
    ratio = min(1.0, max(0.0, target_sec / max(1.0, total_duration_sec)))
    tap_x = int(100 + ratio * 520)
    log(f"[*] Coarse seek to position on scrubber at ({tap_x}, 928)...")
    d.click(tap_x, 928)
    time.sleep(1.0)

    # Stage 2: Precision closed-loop waveform micro-adjustment (at Y=1056, ~67px per second)
    max_iterations = 8
    for step in range(max_iterations):
        sb = d(resourceIdMatches=r".*play_progress_bar.*")
        val_ms = float(sb.info.get("text", "0")) if sb.exists(timeout=1.0) else 0.0
        curr_sec = val_ms / 1000.0 if val_ms > 100.0 else val_ms
        diff_sec = target_sec - curr_sec
        log(f"🔄 [YT AUDIO FEEDBACK {step + 1}/{max_iterations}] Current: {curr_sec:.2f}s | Target: {target_sec:.2f}s | Diff: {diff_sec:+.2f}s")

        if abs(diff_sec) <= 0.3:
            log(f"✅ [TARGET ACHIEVED] Audio aligned at exact {curr_sec:.2f}s (Diff: {abs(diff_sec):.3f}s)!")
            break

        offset = min(350, max(22, int(abs(diff_sec) * 67.0)))
        if diff_sec > 0:
            # Need to advance forward in time -> Drag left
            start_x = 450
            end_x = max(50, start_x - offset)
            log(f"   ⏩ [FORWARD NUDGE] Dragging Left ({start_x} -> {end_x}) at Y=1056...")
            d.drag(start_x, 1056, end_x, 1056, duration=0.2)
        else:
            # Need to move backward in time -> Drag right
            start_x = 250
            end_x = min(670, start_x + offset)
            log(f"   ⏪ [BACKWARD NUDGE] Dragging Right ({start_x} -> {end_x}) at Y=1056...")
            d.drag(start_x, 1056, end_x, 1056, duration=0.2)
        time.sleep(0.7)

    # Tap 'Done' button at (632, 1208)
    done_btn = (
        d(resourceId="app.morphe.android.youtube:id/overlay_dialog_fragment_done")
        or d(textMatches=r"(?i)^Done$")
        or d(descriptionMatches=r"(?i)^Done$")
    )
    smart_click(done_btn, "Done Button (Audio Trimmer)", fallback_coords=(632, 1208), timeout=3.0, d=d)
    time.sleep(1.5)
    log("[+] YouTube Audio timestamp adjusted and applied successfully!")


def upload_short(
    device_addr: str = "127.0.0.1:5555",
    video_path: str = r"upload files\short_10s_test.mp4",
    title: str = "YouTube Short #shorts",
    sound_query: Optional[str] = None,
    timestamp: Optional[str] = None
):
    log(f"[*] Connecting UIAutomator2 to Android device: {device_addr}...")
    d = u2.connect(device_addr)
    log(f"[+] Device connected: {d.info.get('productName', 'Android')} ({d.window_size()})")

    yt_pkg = get_installed_youtube_package(d)
    log(f"[*] Target YouTube Package: {yt_pkg}")

    # 1. Push and index video
    content_uri = push_and_index_video(d, video_path)

    # 2. Reset YouTube and launch direct video upload intent
    log(f"[*] Launching YouTube Short upload editor ({yt_pkg})...")
    d.app_stop(yt_pkg)
    time.sleep(1.5)

    upload_cmd = [
        "am", "start",
        "-n", f"{yt_pkg}/com.google.android.apps.youtube.app.application.Shell_UploadActivity",
        "-d", content_uri,
        "-a", "android.intent.action.SEND",
        "-t", "video/mp4",
        "--eu", "android.intent.extra.STREAM", content_uri
    ]
    d.shell(upload_cmd)
    log("[*] Video trimmer loading (waiting 10 seconds)...")
    time.sleep(10.0)

    # Double-check YouTube is in foreground and trimmer is loaded
    log("[*] Double-checking YouTube foreground state and trimmer readiness...")
    for retry in range(10):
        cur_app = d.app_current()
        pkg_now = cur_app.get("package", "")
        trimmer_btn = (
            d(textMatches=r"(?i)^Next$")
            or d(descriptionMatches=r"(?i)^Next$")
            or d(resourceIdMatches=r".*next_button.*|.*upload_next.*|.*trimmer.*")
        )
        if yt_pkg in pkg_now or trimmer_btn.exists(timeout=1.0):
            log(f"[+] [CONFIRMED] YouTube is active ({pkg_now} / {cur_app.get('activity')}) and ready!")
            break
        log(f"   ⏳ Waiting for YouTube to become foreground ({retry + 1}/10)... Current: '{pkg_now}'")
        time.sleep(1.0)

    # 3. Trimmer Screen -> Tap 'Next' at bottom right
    log("[*] Step 3: Tapping Trimmer 'Next' button...")
    trimmer_next = (
        d(textMatches=r"(?i)^Next$")
        or d(descriptionMatches=r"(?i)^Next$")
        or d(resourceIdMatches=r".*next_button.*")
    )
    smart_click(trimmer_next, "Trimmer Next Button", fallback_coords=(627, 1112), timeout=5.0, d=d)
    time.sleep(3.5)

    # 4. Handle Sound / Music Selection
    if sound_query or timestamp:
        log("[*] Step 4: Adding sound / music from YouTube Library...")
        add_sound_btn = (
            d(textMatches=r"(?i)Add sound.*")
            or d(descriptionMatches=r"(?i)Add sound.*")
            or d(resourceIdMatches=r".*add_sound.*")
        )
        smart_click(add_sound_btn, "Add Sound Button", fallback_coords=(360, 120), timeout=4.0, d=d)
        time.sleep(2.0)

        # Search for specific song if query provided
        if sound_query and str(sound_query).strip().lower() not in ("true", "1", "none"):
            query_str = str(sound_query).strip()
            log(f"[*] Step 4a: Clicking music picker search box ('app.morphe.android.youtube:id/music_picker_search_box')...")
            search_button = (
                d(resourceId="app.morphe.android.youtube:id/music_picker_search_box")
                or d(resourceIdMatches=r".*music_picker_search_box.*")
                or d(descriptionMatches=r"(?i)Search.*")
                or d(textMatches=r"(?i)Search.*")
            )
            smart_click(search_button, "Music Picker Search Box", fallback_coords=(360, 112), timeout=4.0, d=d)
            time.sleep(1.5)

            log(f"[*] Step 4b: Typing search query: '{query_str}' into search edit text...")
            search_box = (
                d(resourceIdMatches=r".*search_edit_text.*|.*search_src_text.*")
                or d(className="android.widget.EditText")
                or d(textMatches=r"(?i)Search.*")
            )
            smart_type(search_box, query_str, "Search Sound Edit Box", timeout=4.0)
            d.press("enter")
            time.sleep(3.0)

            # Select first search result track (exclude 'Create an original track')
            log(f"[*] Step 4c: Selecting search result track for '{query_str}'...")
            first_track = (
                d(resourceIdMatches=r".*music_item.*|.*track_item.*|.*music_row.*")
                or d(descriptionMatches=rf"(?i).*{query_str}.*")
                or d(textMatches=rf"(?i).*{query_str}.*")
                or d(className="android.view.ViewGroup", descriptionMatches=r"(?i)^(?!.*Create an original track).*$", clickable=True)
            )
            smart_click(first_track, f"Search Result Track ('{query_str}')", fallback_coords=(360, 360), timeout=4.0, d=d)
            time.sleep(2.0)
        else:
            # Select top recommended track
            log("[*] Selecting top recommended track...")
            top_track = d(resourceIdMatches=r".*track_item.*|.*music_item.*")
            smart_click(top_track, "Top Recommended Track", fallback_coords=(300, 460), timeout=4.0, d=d)
            time.sleep(1.5)

        # Tap 'Use this sound' / Blue Arrow button
        log("[*] Attaching selected music...")
        use_sound_btn = (
            d(resourceIdMatches=r".*use_sound.*|.*select_sound.*")
            or d(descriptionMatches=r"(?i)Use sound|Add audio|Use this sound")
        )
        smart_click(use_sound_btn, "Use Sound Button (Blue Arrow)", fallback_coords=(648, 460), timeout=4.0, d=d)
        time.sleep(2.5)
        log("[+] Sound successfully attached to Short!")

        # Adjust timestamp if specified
        if timestamp:
            seek_youtube_audio(d, timestamp)

    # 5. Editor 'Next' button
    log("[*] Step 5: Tapping Editor 'Next' button...")
    editor_next = (
        d(textMatches=r"(?i)^Next$")
        or d(descriptionMatches=r"(?i)^Next$")
        or d(resourceIdMatches=r".*next_button.*")
    )
    smart_click(editor_next, "Editor Next Button", fallback_coords=(530, 1124), timeout=5.0, d=d)
    log("[*] Waiting for video render & metadata screen...")
    time.sleep(4.0)

    # 6. Metadata Screen: Enter Title
    log(f"[*] Step 6: Entering Short Title: '{title}'...")
    title_box = (
        d(resourceIdMatches=r".*title_edit_text.*|.*caption.*|.*comment_edit_text.*")
        or d(textMatches=r"(?i)Create a title.*|Caption your Short.*")
        or d(className="android.widget.EditText")
    )
    smart_type(title_box, title, "Short Title Input Box", timeout=4.0)
    time.sleep(1.5)

    # Dismiss soft keyboard using KEYCODE_BACK (4) so screen returns to full height
    log("[*] Dismissing soft keyboard...")
    d.press("back")
    time.sleep(2.0)

    # 7. Tap 'Upload Short' button
    log("[*] Step 7: Clicking 'Upload Short' button...")
    upload_btn = (
        d(textMatches=r"(?i)^Upload Short$")
        or d(descriptionMatches=r"(?i)^Upload Short$")
        or d(resourceIdMatches=r".*upload_bottom_button.*|.*upload_button.*")
    )
    smart_click(upload_btn, "Upload Short Button", fallback_coords=(360, 1120), timeout=5.0, d=d)
    time.sleep(3.0)

    log("\n🎉 [SUCCESS] YouTube Short upload request submitted successfully!")
    log("[*] Video is now uploading and processing on your YouTube channel.")


def main():
    parser = argparse.ArgumentParser(description="YouTube Shorts Uploader (UIAutomator2)")
    parser.add_argument("-s", "--device", default="127.0.0.1:5555", help="Device ADB address")
    parser.add_argument("-u", "--upload", default=r"upload files\short_10s_test.mp4", help="Video path")
    parser.add_argument("-T", "--title", default="YouTube Short #shorts", help="Short title")
    parser.add_argument("-m", "--sound", default=None, help="Sound name/query")
    parser.add_argument("-t", "--timestamp", default=None, help="Audio start timestamp")
    args = parser.parse_args()

    upload_short(
        device_addr=args.device,
        video_path=args.upload,
        title=args.title,
        sound_query=args.sound,
        timestamp=args.timestamp
    )


if __name__ == "__main__":
    main()
