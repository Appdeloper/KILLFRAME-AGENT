"""
KILLFRAME-AGENT Pipeline Validator
Validates every single step before and after execution.
If anything is wrong it fixes it automatically.
Never lets bad output through.
"""
import os
import cv2
import numpy as np
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def validate_footage(footage_folder):
    """Check footage exists and is readable"""
    print("[VALIDATOR] Checking footage...")
    folder = Path(footage_folder)
    if not folder.exists():
        raise FileNotFoundError(f"Footage folder not found: {footage_folder}")

    videos = list(folder.glob("*.mp4")) + list(folder.glob("*.avi")) + list(folder.glob("*.mov")) + list(folder.glob("*.mkv"))
    if not videos:
        raise FileNotFoundError(f"No video files found in {footage_folder}")

    valid_videos = []
    for v in videos:
        if v.stat().st_size < 10000:
            print(f"[VALIDATOR] Skip tiny file: {v.name}")
            continue
        cap = cv2.VideoCapture(str(v))
        if not cap.isOpened():
            print(f"[VALIDATOR] Cannot open: {v.name}")
            cap.release()
            continue
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if frames < 30 or fps < 1:
            print(f"[VALIDATOR] Invalid video: {v.name}")
            continue
        duration = frames / fps
        valid_videos.append(str(v))
        print(f"[VALIDATOR] [OK] Valid footage: {v.name} ({duration:.1f}s)")

    if not valid_videos:
        raise ValueError("No valid video files found in footage folder")
    return valid_videos

def validate_music(music_path):
    """Check music file exists and is readable"""
    print("[VALIDATOR] Checking music...")
    if not music_path or music_path == "AUTO":
        return True
    if not os.path.exists(music_path):
        raise FileNotFoundError(f"Music file not found: {music_path}")
    size = os.path.getsize(music_path)
    if size < 1000:
        raise ValueError(f"Music file too small: {size} bytes")
    print(f"[VALIDATOR] [OK] Music valid: {os.path.basename(music_path)} ({size/1024/1024:.1f}MB)")
    return True

def validate_clips(clips):
    """Check all extracted clips are valid and not corrupt"""
    print(f"[VALIDATOR] Validating {len(clips)} extracted clips...")
    valid = []
    corrupt = []

    for item in clips:
        path = item["path"] if isinstance(item, dict) else item
        if not os.path.exists(path):
            corrupt.append(path)
            print(f"[VALIDATOR] [FAIL] Missing: {path}")
            continue
        size = os.path.getsize(path)
        if size < 5000:
            corrupt.append(path)
            print(f"[VALIDATOR] [FAIL] Too small: {path} ({size} bytes)")
            continue
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            corrupt.append(path)
            print(f"[VALIDATOR] [FAIL] Corrupt: {path}")
            cap.release()
            continue
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None or frames < 5:
            corrupt.append(path)
            print(f"[VALIDATOR] [FAIL] Unreadable: {path}")
            continue
        if frame.mean() < 3:
            corrupt.append(path)
            print(f"[VALIDATOR] [FAIL] Black frame: {path}")
            continue
        valid.append(item)
        print(f"[VALIDATOR] [OK] Clip OK: {os.path.basename(path)} ({frames} frames)")

    print(f"[VALIDATOR] Valid clips: {len(valid)} | Corrupt/missing: {len(corrupt)}")
    if len(valid) == 0:
        raise ValueError("No valid clips after validation — all clips are corrupt or missing")
    return valid

def validate_beat_timeline(beat_timeline):
    """Check beat timeline has valid data"""
    print("[VALIDATOR] Checking beat timeline...")
    if not beat_timeline:
        raise ValueError("Beat timeline is empty")
    timestamps = beat_timeline.get("timestamps", [])
    if not timestamps or len(timestamps) < 2:
        print("[VALIDATOR] [WARNING] Too few beats — generating fallback timeline")
        fallback = [i * 2.5 for i in range(60)]
        beat_timeline["timestamps"] = fallback
        beat_timeline["total_beats"] = len(fallback)
        beat_timeline["avg_gap_seconds"] = 2.5
        beat_timeline["recommended_clip_length"] = 2.5
    if beat_timeline.get("total_beats", 0) == 0:
        beat_timeline["total_beats"] = len(timestamps)
    print(f"[VALIDATOR] [OK] Beats valid: {beat_timeline['total_beats']} beats")
    return beat_timeline

def validate_output(output_path, min_duration=5.0, min_size_mb=0.5):
    """Check final output is valid"""
    print(f"[VALIDATOR] Checking output: {output_path}")
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Output not created: {output_path}")
    size_mb = os.path.getsize(output_path) / (1024*1024)
    if size_mb < min_size_mb:
        raise ValueError(f"Output too small: {size_mb:.2f}MB")
    cap = cv2.VideoCapture(output_path)
    if not cap.isOpened():
        raise ValueError(f"Output cannot be opened: {output_path}")
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    duration = frames / fps
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise ValueError("Output has no readable frames")
    if frame.mean() < 5:
        raise ValueError("Output is black — color grading failed")
    if duration < min_duration:
        raise ValueError(f"Output too short: {duration:.1f}s")
    print(f"[VALIDATOR] [OK] Output valid: {duration:.1f}s | {size_mb:.1f}MB | brightness:{frame.mean():.0f}")
    return True
