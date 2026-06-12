"""Run this to check everything is working before editing"""
import os, sys, cv2, numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

checks = {
    "opencv": lambda: cv2.__version__,
    "numpy": lambda: np.__version__,
    "moviepy": lambda: __import__("moviepy").__version__,
    "librosa": lambda: __import__("librosa").__version__,
    "yt_dlp": lambda: __import__("yt_dlp").version.__version__,
    "ffmpeg": lambda: os.system("ffmpeg -version >nul 2>&1") == 0,
    "dotenv": lambda: "installed" if __import__("dotenv") else "failed",
}

print("="*45)
print("  KILLFRAME-AGENT Health Check")
print("="*45)
all_ok = True
for lib, check in checks.items():
    try:
        result = check()
        print(f"  [OK] {lib}: {result}")
    except Exception as e:
        print(f"  [FAIL] {lib}: MISSING -- pip install {lib}")
        all_ok = False

print("="*45)
if all_ok:
    print("  ALL SYSTEMS GO -- Ready to edit!")
else:
    print("  Fix missing libraries then run again")
print("="*45)
