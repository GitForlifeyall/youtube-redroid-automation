"""
Interactive Coordinate Inspector for Android / LDPlayer
========================================================
Usage:
  python get_coords.py
     -> Opens an interactive window with the live screen.
     -> Hover to see real-time coordinates.
     -> Click anywhere to print (X, Y) and copy code to clipboard.
     -> Press 'R' or 'SPACE' to refresh screen.

  python get_coords.py --live
     -> Listens to taps on LDPlayer / Phone in real-time and prints (X, Y).
"""

import sys
import os
import subprocess
import argparse
import tkinter as tk
from tkinter import Canvas
import io

try:
    from PIL import Image, ImageTk
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image, ImageTk


def find_adb():
    paths = [
        r"C:\leidian\LDPlayer9\adb.exe",
        r"C:\LDPlayer\LDPlayer9\adb.exe",
        r"C:\Users\Shahid\tools\scrcpy\adb.exe",
        r"C:\platform-tools\adb.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "adb"


def capture_screenshot(adb_exe, target="127.0.0.1:5555"):
    try:
        cmd = [adb_exe, "-s", target, "exec-out", "screencap", "-p"]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode == 0 and len(proc.stdout) > 1000:
            # Fix Windows CRLF in stdout if any
            data = proc.stdout.replace(b"\r\r\n", b"\n").replace(b"\r\n", b"\n")
            return Image.open(io.BytesIO(data))
    except Exception:
        pass
    
    # Fallback to temp file
    try:
        subprocess.run([adb_exe, "-s", target, "shell", "screencap", "-p", "/sdcard/_screen_tmp.png"], capture_output=True)
        subprocess.run([adb_exe, "-s", target, "pull", "/sdcard/_screen_tmp.png", "_screen_tmp.png"], capture_output=True)
        if os.path.exists("_screen_tmp.png"):
            img = Image.open("_screen_tmp.png")
            return img
    except Exception as e:
        print(f"Error taking screenshot: {e}")
    return None


class CoordinateViewer:
    def __init__(self, adb_exe, target="127.0.0.1:5555"):
        self.adb_exe = adb_exe
        self.target = target
        
        self.root = tk.Tk()
        self.root.title(f"Android Coordinate Inspector [{target}] - Click anywhere to copy (X, Y)")
        self.root.geometry("450x850")
        self.root.configure(bg="#1e1e2e")
        
        # Info bar
        self.status_var = tk.StringVar(value="Hover to see (X,Y) | Left Click: Copy (X,Y) | Press 'R': Refresh")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, font=("Consolas", 11, "bold"),
                                   bg="#11111b", fg="#a6e3a1", pady=8)
        self.status_bar.pack(fill=tk.X, side=tk.TOP)
        
        # Canvas
        self.canvas = Canvas(self.root, bg="#181825", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.orig_image = None
        self.display_image = None
        self.tk_image = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        
        # Bindings
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", lambda e: self.refresh_screen())
        self.root.bind("<r>", lambda e: self.refresh_screen())
        self.root.bind("<R>", lambda e: self.refresh_screen())
        self.root.bind("<space>", lambda e: self.refresh_screen())
        
        self.refresh_screen()

    def refresh_screen(self):
        self.status_var.set("Capturing screen from Android...")
        self.root.update()
        
        img = capture_screenshot(self.adb_exe, self.target)
        if img is None:
            self.status_var.set(f"Error: Could not capture screen from {self.target}")
            return
            
        self.orig_image = img
        orig_w, orig_h = img.size
        
        # Scale to fit window
        canvas_h = 760
        ratio = canvas_h / float(orig_h)
        canvas_w = int(orig_w * ratio)
        
        self.display_w = canvas_w
        self.display_h = canvas_h
        self.scale_x = orig_w / float(canvas_w)
        self.scale_y = orig_h / float(canvas_h)
        
        resized = img.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.status_var.set(f"Ready ({orig_w}x{orig_h}). Hover or Click anywhere | Press 'R' to Refresh")

    def on_mouse_move(self, event):
        if self.orig_image is None:
            return
        x_real = int(event.x * self.scale_x)
        y_real = int(event.y * self.scale_y)
        
        # Clamp to bounds
        w, h = self.orig_image.size
        x_real = max(0, min(w, x_real))
        y_real = max(0, min(h, y_real))
        
        self.status_var.set(f"Cursor: X = {x_real} , Y = {y_real}  |  Click to copy tap({x_real}, {y_real})")

    def on_click(self, event):
        if self.orig_image is None:
            return
        x_real = int(event.x * self.scale_x)
        y_real = int(event.y * self.scale_y)
        
        code_str = f"tap(adb_exe, target, {x_real}, {y_real})"
        
        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(code_str)
        
        # Visual feedback: Draw a red crosshair
        self.canvas.delete("crosshair")
        r = 8
        self.canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r, outline="#f38ba8", width=2, tags="crosshair")
        self.canvas.create_line(event.x - 15, event.y, event.x + 15, event.y, fill="#f38ba8", width=2, tags="crosshair")
        self.canvas.create_line(event.x, event.y - 15, event.x, event.y + 15, fill="#f38ba8", width=2, tags="crosshair")
        
        print(f"\n[COORDINATE COPIED]: X = {x_real}, Y = {y_real} -> {code_str}")
        self.status_var.set(f"COPIED TO CLIPBOARD: X = {x_real}, Y = {y_real} -> {code_str}")

    def run(self):
        self.root.mainloop()


def listen_live_taps(adb_exe, target="127.0.0.1:5555"):
    print(f"[*] Listening for live touch events on {target}...")
    print("[*] Touch or click anywhere on the emulator/phone screen!")
    print("[*] Press Ctrl+C to stop.\n")
    
    cmd = [adb_exe, "-s", target, "shell", "getevent", "-l"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    
    cur_raw_35 = None
    cur_raw_36 = None
    
    try:
        for line in proc.stdout:
            parts = line.strip().split()
            if len(parts) >= 4:
                event_type = parts[1]
                event_code = parts[2]
                event_value = parts[3]
                
                # ABS_MT_POSITION_X or ABS_MT_POSITION_Y
                if "ABS_MT_POSITION_X" in event_code or "0035" in event_code:
                    try:
                        cur_raw_35 = int(event_value, 16)
                    except ValueError:
                        pass
                elif "ABS_MT_POSITION_Y" in event_code or "0036" in event_code:
                    try:
                        cur_raw_36 = int(event_value, 16)
                    except ValueError:
                        pass
                elif "SYN_REPORT" in event_code and cur_raw_35 is not None and cur_raw_36 is not None:
                    # In portrait Android emulators: 0036 is X (0-720), 0035 is Y (0-1280)
                    if cur_raw_35 > 720 or cur_raw_36 <= 720:
                        screen_x = cur_raw_36
                        screen_y = cur_raw_35
                    else:
                        screen_x = cur_raw_35
                        screen_y = cur_raw_36

                    print(f"🎯 [TOUCH DETECTED]: X = {screen_x}, Y = {screen_y}  -->  tap(adb_exe, target, {screen_x}, {screen_y})")
                    cur_raw_35 = None
                    cur_raw_36 = None
    except KeyboardInterrupt:
        print("\n[*] Stopped listening.")
    finally:
        proc.kill()


def main():
    parser = argparse.ArgumentParser(description="Android Coordinate Inspector")
    parser.add_argument("-s", "--target", default="127.0.0.1:5555", help="ADB target device")
    parser.add_argument("--live", action="store_true", help="Live tap event logger")
    args = parser.parse_args()
    
    adb_exe = find_adb()
    
    if args.live:
        listen_live_taps(adb_exe, args.target)
    else:
        app = CoordinateViewer(adb_exe, args.target)
        app.run()


if __name__ == "__main__":
    main()
