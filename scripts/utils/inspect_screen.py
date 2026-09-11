import subprocess
import xml.etree.ElementTree as ET

adb_exe = r"C:\Users\Shahid\tools\scrcpy\adb.exe"
target = "127.0.0.1:5801"

subprocess.run([adb_exe, "-s", target, "shell", "uiautomator", "dump", "--compressed", "/sdcard/dump.xml"], capture_output=True)
res = subprocess.check_output([adb_exe, "-s", target, "shell", "cat", "/sdcard/dump.xml"]).decode('utf-8', 'ignore')

root = ET.fromstring(res)
for elem in root.iter('node'):
    txt = elem.attrib.get('text') or elem.attrib.get('content-desc') or elem.attrib.get('resource-id')
    if txt or elem.attrib.get('clickable') == 'true':
        print(f"{elem.attrib.get('bounds')}: text='{elem.attrib.get('text')}' desc='{elem.attrib.get('content-desc')}' id='{elem.attrib.get('resource-id')}' class='{elem.attrib.get('class')}' clickable={elem.attrib.get('clickable')}")
