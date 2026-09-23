import os
import subprocess
import zipfile
import shutil

STUB_C = """
#include <stdint.h>

__attribute__((visibility("default"))) int JNI_OnLoad(void* vm, void* reserved) {
    return 0x00010006; // JNI_VERSION_1_6
}

__attribute__((visibility("default"))) void JNI_OnUnload(void* vm, void* reserved) {}

// Generic empty stubs for symbols
__attribute__((visibility("default"))) int nRecordDataInNightWatch(int a, int b, int64_t c, int d) { return 0; }
__attribute__((visibility("default"))) int nRecordTickInNightWatch(int a, int b, int64_t c, int64_t d, int64_t e, int64_t f) { return 0; }
__attribute__((visibility("default"))) int nSaveResourceData(int a, int b) { return 1; }
__attribute__((visibility("default"))) int initNightWatch(const char* a, const char* b, int c, int d, int e, int f) { return 0; }
__attribute__((visibility("default"))) void sigmux_init(void) {}
__attribute__((visibility("default"))) void sigmux_install(void) {}
__attribute__((visibility("default"))) void breakpad_init(void) {}
"""

def build_stub_so():
    os.makedirs("scratch", exist_ok=True)
    c_path = os.path.abspath("scratch/stub.c")
    so_path = os.path.abspath("scratch/stub.so")
    
    with open(c_path, "w") as f:
        f.write(STUB_C)
        
    wsl_c = subprocess.check_output(["wsl", "-d", "Ubuntu", "-u", "root", "-e", "wslpath", "-a", c_path.replace("\\", "/")]).decode().strip()
    wsl_so = subprocess.check_output(["wsl", "-d", "Ubuntu", "-u", "root", "-e", "wslpath", "-a", so_path.replace("\\", "/")]).decode().strip()
    
    cmd = f"aarch64-linux-gnu-gcc -shared -fPIC -O2 -nostdlib '{wsl_c}' -o '{wsl_so}'"
    subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "-e", "bash", "-c", cmd], check=True)
    print(f"[+] Compiled ARM64 stub .so: {so_path} ({os.path.getsize(so_path)} bytes)")
    return so_path

def patch_and_install():
    stub_so = build_stub_so()
    with open(stub_so, "rb") as f:
        stub_data = f.read()
        
    in_apk = os.path.abspath("downloads/insta_278/com.instagram.android@278.0.0.22.117.apk")
    out_apk = os.path.abspath("downloads/Instagram_Full_Working.apk")
    temp_apk = out_apk + ".tmp.apk"
    
    CRASH_LIBS = {
        "lib/arm64-v8a/libwatcher_binary.so",
        "lib/arm64-v8a/libsigmux.so",
        "lib/arm64-v8a/libbreakpad.so",
        "lib/arm64-v8a/libbreakpad_cpp_helper.so",
        "lib/arm64-v8a/liblmkd_detector_binary.so",
        "lib/arm64-v8a/libunwindstack_binary.so",
    }
    
    print(f"[*] Packaging {out_apk} with ARM64 no-op crash monitor stubs...")
    with zipfile.ZipFile(in_apk, 'r') as zin, zipfile.ZipFile(temp_apk, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename.startswith("META-INF/") and not item.filename.startswith("META-INF/services/"):
                continue
            if item.filename in CRASH_LIBS:
                print(f"[+] Replacing with safe stub: {item.filename}")
                zout.writestr(item.filename, stub_data)
            else:
                zout.writestr(item, zin.read(item.filename))
                
    print("[*] Signing APK via WSL apksigner...")
    wsl_in = subprocess.check_output(["wsl", "-d", "Ubuntu", "-u", "root", "-e", "wslpath", "-a", temp_apk.replace("\\", "/")]).decode().strip()
    wsl_out = subprocess.check_output(["wsl", "-d", "Ubuntu", "-u", "root", "-e", "wslpath", "-a", out_apk.replace("\\", "/")]).decode().strip()
    
    sign_cmd = f"apksigner sign --ks /root/debug.keystore --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android --out '{wsl_out}' '{wsl_in}'"
    subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "-e", "bash", "-c", sign_cmd], check=True)
    
    if os.path.exists(temp_apk):
        os.remove(temp_apk)
        
    print(f"[+] Successfully built signed Instagram: {out_apk}")
    
    adb = r"C:\Users\Shahid\tools\scrcpy\adb.exe"
    target = "127.0.0.1:5801"
    
    print("[*] Installing on device...")
    subprocess.run([adb, "-s", target, "uninstall", "com.instagram.android"], capture_output=True)
    res = subprocess.run([adb, "-s", target, "install", out_apk], capture_output=True, text=True)
    print(res.stdout)
    print(res.stderr)
    
    print("[*] Starting Instagram Activity...")
    subprocess.run([adb, "-s", target, "shell", "am", "start", "-n", "com.instagram.android/com.instagram.android.activity.MainTabActivity"], check=True)

if __name__ == "__main__":
    patch_and_install()
