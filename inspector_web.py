"""
Chrome-Style Android UI Element & XPath Inspector
==================================================
Runs a local web server (http://localhost:8080) with a Chrome DevTools-like interface:
  - Hover over any element to inspect its text, resource-id, content-desc, class, and bounds.
  - Generates ready-to-copy Python UIAutomator2 code & XPath.
  - Refresh live screen with 1 click.
"""

import sys
import os
import io
import json
import base64
import subprocess
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from typing import Dict, Any, List

ADB_TARGET = "127.0.0.1:5555"


def get_adb():
    paths = [
        r"C:\leidian\LDPlayer9\adb.exe",
        r"C:\LDPlayer\LDPlayer9\adb.exe",
        r"C:\Users\Shahid\tools\scrcpy\adb.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "adb"


def capture_state():
    adb = get_adb()
    
    # 1. Screenshot
    img_b64 = ""
    try:
        subprocess.run([adb, "-s", ADB_TARGET, "shell", "screencap", "-p", "/sdcard/_insp_screen.png"], capture_output=True, timeout=5)
        subprocess.run([adb, "-s", ADB_TARGET, "pull", "/sdcard/_insp_screen.png", "_insp_screen.png"], capture_output=True, timeout=5)
        if os.path.exists("_insp_screen.png"):
            with open("_insp_screen.png", "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Screenshot error: {e}")

    # 2. UI Dump
    nodes_data = []
    try:
        subprocess.run([adb, "-s", ADB_TARGET, "shell", "uiautomator", "dump", "--compressed", "/sdcard/_insp_dump.xml"], capture_output=True, timeout=5)
        xml_bytes = subprocess.run([adb, "-s", ADB_TARGET, "shell", "cat", "/sdcard/_insp_dump.xml"], capture_output=True, timeout=4).stdout
        xml_str = xml_bytes.decode("utf-8", errors="replace")
        
        if "<hierarchy" in xml_str:
            clean_xml = xml_str[xml_str.find("<hierarchy"):]
            root = ET.fromstring(clean_xml)
            
            def parse_node(n, parent_path=""):
                attribs = n.attrib
                bounds_str = attribs.get("bounds", "")
                
                # Parse [x1, y1][x2, y2]
                box = None
                if bounds_str and "[" in bounds_str:
                    try:
                        pts = bounds_str.replace("][", ",").replace("[", "").replace("]", "").split(",")
                        if len(pts) == 4:
                            x1, y1, x2, y2 = map(int, pts)
                            if x2 > x1 and y2 > y1:
                                box = {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}
                    except Exception:
                        pass
                
                text = attribs.get("text", "")
                res_id = attribs.get("resource-id", "")
                desc = attribs.get("content-desc", "")
                cls_name = attribs.get("class", "")
                
                # Build XPath
                xpath = ""
                if res_id:
                    short_id = res_id.split("/")[-1] if "/" in res_id else res_id
                    xpath = f'//{cls_name}[@resource-id="{res_id}"]'
                elif text:
                    xpath = f'//{cls_name}[@text="{text}"]'
                elif desc:
                    xpath = f'//{cls_name}[@content-desc="{desc}"]'
                else:
                    xpath = f'//{cls_name}'

                # Build U2 Selector
                u2_code = ""
                if text:
                    u2_code = f'd(text="{text}")'
                elif desc:
                    u2_code = f'd(description="{desc}")'
                elif res_id:
                    u2_code = f'd(resourceId="{res_id}")'
                else:
                    u2_code = f'd(className="{cls_name}")'

                if box:
                    nodes_data.append({
                        "box": box,
                        "text": text,
                        "res_id": res_id,
                        "desc": desc,
                        "class": cls_name,
                        "xpath": xpath,
                        "u2": u2_code,
                    })

                for child in n:
                    parse_node(child)

            parse_node(root)
    except Exception as e:
        print(f"UI Dump error: {e}")

    return {"image": img_b64, "nodes": nodes_data}


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Android Chrome DevTools Inspector</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }
        body { background: #181825; color: #cdd6f4; display: flex; height: 100vh; overflow: hidden; }
        
        #left-pane { flex: 0 0 460px; background: #11111b; display: flex; flex-direction: column; align-items: center; padding: 12px; border-right: 1px solid #313244; position: relative; }
        #screen-container { position: relative; width: 360px; height: 640px; background: #000; border: 2px solid #45475a; border-radius: 8px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        #screen-img { width: 100%; height: 100%; object-fit: contain; pointer-events: none; user-select: none; }
        #overlay-canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; cursor: crosshair; }

        #right-pane { flex: 1; display: flex; flex-direction: column; padding: 16px; overflow-y: auto; background: #181825; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid #313244; padding-bottom: 12px; }
        .title { font-size: 18px; font-weight: bold; color: #89b4fa; }
        .btn-refresh { background: #a6e3a1; color: #11111b; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-refresh:hover { background: #94e2d5; }

        .card { background: #1e1e2e; border: 1px solid #313244; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .card-title { font-size: 14px; font-weight: bold; color: #f9e2af; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }
        
        .prop-row { display: flex; margin-bottom: 10px; align-items: center; }
        .prop-label { flex: 0 0 120px; font-size: 12px; color: #a6adc8; text-transform: uppercase; letter-spacing: 0.5px; }
        .prop-val { flex: 1; font-size: 13px; color: #f5e0dc; background: #313244; padding: 6px 10px; border-radius: 4px; word-break: break-all; }
        .btn-copy { margin-left: 8px; background: #45475a; color: #cdd6f4; border: none; padding: 6px 10px; border-radius: 4px; font-size: 11px; cursor: pointer; }
        .btn-copy:hover { background: #89b4fa; color: #11111b; }

        .highlight-box { position: absolute; border: 2px solid #89b4fa; background: rgba(137, 180, 250, 0.25); pointer-events: none; transition: all 0.05s ease-out; }
        .toast { position: fixed; bottom: 20px; right: 20px; background: #a6e3a1; color: #11111b; padding: 10px 18px; border-radius: 6px; font-weight: bold; display: none; }
    </style>
</head>
<body>

    <div id="left-pane">
        <div style="margin-bottom: 10px; width: 100%; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; color: #a6adc8;">Live Android Screen</span>
            <span id="coords-text" style="font-size: 12px; color: #f9e2af; font-weight: bold;">X: 0, Y: 0</span>
        </div>
        <div id="screen-container">
            <img id="screen-img" src="" alt="Screen">
            <canvas id="overlay-canvas"></canvas>
            <div id="hover-highlight" class="highlight-box" style="display: none;"></div>
        </div>
    </div>

    <div id="right-pane">
        <div class="header">
            <div class="title">🔍 Android Element Inspector (Chrome Style)</div>
            <button class="btn-refresh" onclick="refreshData()">🔄 Refresh Screen</button>
        </div>

        <div class="card">
            <div class="card-title">Selected Element Details</div>
            
            <div class="prop-row">
                <span class="prop-label">UIAutomator2:</span>
                <span class="prop-val" id="val-u2">Hover over any element</span>
                <button class="btn-copy" onclick="copyProp('val-u2')">Copy</button>
            </div>

            <div class="prop-row">
                <span class="prop-label">XPath:</span>
                <span class="prop-val" id="val-xpath">//node</span>
                <button class="btn-copy" onclick="copyProp('val-xpath')">Copy</button>
            </div>

            <div class="prop-row">
                <span class="prop-label">Text:</span>
                <span class="prop-val" id="val-text">-</span>
                <button class="btn-copy" onclick="copyProp('val-text')">Copy</button>
            </div>

            <div class="prop-row">
                <span class="prop-label">Resource ID:</span>
                <span class="prop-val" id="val-id">-</span>
                <button class="btn-copy" onclick="copyProp('val-id')">Copy</button>
            </div>

            <div class="prop-row">
                <span class="prop-label">Content Desc:</span>
                <span class="prop-val" id="val-desc">-</span>
                <button class="btn-copy" onclick="copyProp('val-desc')">Copy</button>
            </div>

            <div class="prop-row">
                <span class="prop-label">Class Name:</span>
                <span class="prop-val" id="val-class">-</span>
                <button class="btn-copy" onclick="copyProp('val-class')">Copy</button>
            </div>

            <div class="prop-row">
                <span class="prop-label">Bounds (X, Y):</span>
                <span class="prop-val" id="val-bounds">-</span>
                <button class="btn-copy" onclick="copyProp('val-bounds')">Copy</button>
            </div>
        </div>
    </div>

    <div id="toast" class="toast">Copied to clipboard!</div>

    <script>
        let nodes = [];
        let origWidth = 720;
        let origHeight = 1280;

        const container = document.getElementById('screen-container');
        const img = document.getElementById('screen-img');
        const canvas = document.getElementById('overlay-canvas');
        const highlight = document.getElementById('hover-highlight');
        const coordsText = document.getElementById('coords-text');

        function refreshData() {
            fetch('/api/state')
                .then(res => res.json())
                .then(data => {
                    if (data.image) {
                        img.src = 'data:image/png;base64,' + data.image;
                    }
                    nodes = data.nodes || [];
                });
        }

        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            const scaleX = origWidth / rect.width;
            const scaleY = origHeight / rect.height;

            const realX = Math.round(mouseX * scaleX);
            const realY = Math.round(mouseY * scaleY);

            coordsText.innerText = `X: ${realX}, Y: ${realY}`;

            // Find smallest matching node containing point
            let bestNode = null;
            let minArea = Infinity;

            for (const n of nodes) {
                const b = n.box;
                if (realX >= b.x && realX <= (b.x + b.w) && realY >= b.y && realY <= (b.y + b.h)) {
                    const area = b.w * b.h;
                    if (area < minArea) {
                        minArea = area;
                        bestNode = n;
                    }
                }
            }

            if (bestNode) {
                const b = bestNode.box;
                highlight.style.display = 'block';
                highlight.style.left = (b.x / scaleX) + 'px';
                highlight.style.top = (b.y / scaleY) + 'px';
                highlight.style.width = (b.w / scaleX) + 'px';
                highlight.style.height = (b.h / scaleY) + 'px';

                document.getElementById('val-u2').innerText = bestNode.u2;
                document.getElementById('val-xpath').innerText = bestNode.xpath;
                document.getElementById('val-text').innerText = bestNode.text || '-';
                document.getElementById('val-id').innerText = bestNode.res_id || '-';
                document.getElementById('val-desc').innerText = bestNode.desc || '-';
                document.getElementById('val-class').innerText = bestNode.class || '-';
                document.getElementById('val-bounds').innerText = `tap(adb_exe, target, ${Math.round(b.x + b.w/2)}, ${Math.round(b.y + b.h/2)})`;
            }
        });

        function copyProp(elementId) {
            const text = document.getElementById(elementId).innerText;
            navigator.clipboard.writeText(text).then(() => {
                const toast = document.getElementById('toast');
                toast.style.display = 'block';
                setTimeout(() => { toast.style.display = 'none'; }, 1500);
            });
        }

        refreshData();
    </script>
</body>
</html>
"""


class InspectorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/state":
            data = capture_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    port = 8080
    server = HTTPServer(("127.0.0.1", port), InspectorHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n=======================================================")
    print(f"🚀 Android Chrome-Style Inspector Running At:")
    print(f"👉 {url}")
    print(f"=======================================================\n")
    print("[*] Opening in your web browser...")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Inspector stopped.")


if __name__ == "__main__":
    main()
