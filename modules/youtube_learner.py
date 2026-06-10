"""
KILLFRAME-AGENT YouTube Learning Engine
Analyzes 100 Free Fire montage videos and builds
a master style intelligence database
"""
import os
import json
import time
import numpy as np
import cv2
from pathlib import Path

CACHE_FILE = "style_intelligence.json"

FREE_FIRE_CHANNELS = [
    "https://www.youtube.com/watch?v=NwV3DjiXmms",
    "https://www.youtube.com/@RuokFF",
    "https://www.youtube.com/@White444FF",
    "https://www.youtube.com/@Raistar",
    "ytsearch10:free fire montage 2024 best kills",
    "ytsearch10:free fire ranked highlights 2024",
    "ytsearch10:free fire pro player montage",
    "ytsearch10:free fire headshot montage",
    "ytsearch10:free fire booyah highlights",
    "ytsearch10:garena free fire montage viral",
]

def analyze_single_video(video_path):
    """Extract style metrics from one video"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps if fps > 0 else 1.0

    metrics = {
        "brightness_values": [],
        "saturation_values": [],
        "motion_scores": [],
        "cut_timestamps": [],
        "flash_timestamps": [],
        "color_grades": [],
    }

    prev_frame = None
    prev_brightness = 0
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Process every 5th frame
        if frame_idx % 5 != 0:
            frame_idx += 1
            continue

        timestamp = frame_idx / fps if fps > 0 else 0

        # Brightness
        brightness = frame.mean()
        metrics["brightness_values"].append(brightness)

        # Saturation
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        sat = hsv[:,:,1].mean()
        metrics["saturation_values"].append(float(sat))

        # Motion / cut detection
        if prev_frame is not None:
            diff = cv2.absdiff(frame, prev_frame).mean()
            metrics["motion_scores"].append(float(diff))
            # Detect hard cut (sudden large diff)
            if diff > 35:
                metrics["cut_timestamps"].append(float(timestamp))
            # Detect flash
            if brightness > 180 and prev_brightness < 140:
                metrics["flash_timestamps"].append(float(timestamp))

        prev_frame = frame.copy()
        prev_brightness = brightness
        frame_idx += 1

    cap.release()

    if not metrics["cut_timestamps"]:
        return None

    # Calculate cut intervals
    cuts = metrics["cut_timestamps"]
    intervals = np.diff(cuts) if len(cuts) > 1 else [2.5]

    return {
        "duration": duration,
        "avg_brightness": float(np.mean(metrics["brightness_values"])),
        "avg_saturation": float(np.mean(metrics["saturation_values"])),
        "avg_motion": float(np.mean(metrics["motion_scores"])),
        "cuts_per_minute": float(len(cuts) / (duration/60)) if duration > 0 else 0.0,
        "avg_clip_length": float(np.mean(intervals)),
        "min_clip_length": float(np.min(intervals)),
        "max_clip_length": float(np.max(intervals)),
        "flash_count": len(metrics["flash_timestamps"]),
        "flash_ratio": len(metrics["flash_timestamps"]) / max(len(cuts),1),
        "total_cuts": len(cuts),
    }

def learn_from_youtube(reference_url=None, max_videos=100):
    """
    Main learning function — downloads and analyzes up to 100 videos
    Returns master style intelligence
    """
    # Check cache first
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
            if cache.get("video_count", 0) >= 10:
                print(f"[KILLFRAME] Loaded cached intelligence from {cache['video_count']} videos")
                return cache["master_style"]
        except Exception:
            pass

    print("[KILLFRAME] ══════════════════════════════════════")
    print("[KILLFRAME]   KILLFRAME AI LEARNING ENGINE")
    print("[KILLFRAME]   Analyzing Free Fire montage videos...")
    print("[KILLFRAME] ══════════════════════════════════════")

    os.makedirs("learning_cache", exist_ok=True)
    all_metrics = []
    video_count = 0

    # Build search queries
    queries = [
        "ytsearch5:free fire montage 2024 best",
        "ytsearch5:free fire ranked highlights pro",
        "ytsearch5:free fire headshot montage viral",
        "ytsearch5:free fire booyah highlights 2024",
        "ytsearch5:free fire kill montage music sync",
        "ytsearch5:free fire solo vs squad highlights",
        "ytsearch5:free fire sniper montage",
        "ytsearch5:free fire rush gameplay highlights",
        "ytsearch5:free fire pro player kills",
        "ytsearch5:free fire one tap headshot montage",
        "ytsearch5:free fire aggressive gameplay",
        "ytsearch5:free fire ranked booyah highlights",
        "ytsearch5:ruok ff free fire highlights",
        "ytsearch5:free fire mobile montage beat sync",
        "ytsearch5:free fire gaming highlights cinematic",
        "ytsearch5:free fire tournament highlights",
        "ytsearch5:free fire clutch moments",
        "ytsearch5:free fire best kills compilation",
        "ytsearch5:free fire insane plays highlights",
        "ytsearch5:free fire mobile gaming montage",
    ]

    # Add reference URL first if provided
    if reference_url:
        queries.insert(0, reference_url)

    for query in queries:
        if video_count >= max_videos:
            break

        print(f"[KILLFRAME] Searching: {query[:60]}...")

        try:
            import yt_dlp
            output_tmpl = "learning_cache/%(id)s.%(ext)s"
            ydl_opts = {
                "format": "worst[ext=mp4]/worst",
                "outtmpl": output_tmpl,
                "quiet": True,
                "no_warnings": True,
                "playlist_items": "1:5",
                "max_downloads": 5,
                "socket_timeout": 30,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([query])
        except Exception as e:
            print(f"[KILLFRAME] Download issue: {e}")
            continue

        # Analyze downloaded videos
        for f in Path("learning_cache").glob("*.mp4"):
            if video_count >= max_videos:
                break
            try:
                print(f"[KILLFRAME] Analyzing video {video_count+1}/{max_videos}: {f.name[:30]}...")
                metrics = analyze_single_video(str(f))
                if metrics and metrics["cuts_per_minute"] > 0:
                    all_metrics.append(metrics)
                    video_count += 1
                    print(f"[KILLFRAME] ✅ Learned: {metrics['cuts_per_minute']:.1f} cuts/min | {metrics['avg_clip_length']:.1f}s clips | brightness {metrics['avg_brightness']:.0f}")
                # Delete to save space
                f.unlink()
            except Exception as e:
                print(f"[KILLFRAME] Skip: {e}")
                continue

        time.sleep(1)

    if not all_metrics:
        print("[KILLFRAME] Using built-in default intelligence")
        return get_default_intelligence()

    # Build master style from all analyzed videos
    print(f"\n[KILLFRAME] ══════════════════════════════════════")
    print(f"[KILLFRAME] LEARNING COMPLETE — {video_count} videos analyzed")
    print(f"[KILLFRAME] Building master style intelligence...")

    master = build_master_style(all_metrics)

    # Cache for future runs
    cache_data = {
        "video_count": video_count,
        "master_style": master,
        "individual_metrics": all_metrics
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=2)

    print_intelligence_report(master, video_count)
    return master

def build_master_style(all_metrics):
    """Build unified style intelligence from all analyzed videos"""
    cuts_per_min = [m["cuts_per_minute"] for m in all_metrics]
    clip_lengths = [m["avg_clip_length"] for m in all_metrics]
    brightnesses = [m["avg_brightness"] for m in all_metrics]
    saturations = [m["avg_saturation"] for m in all_metrics]
    flash_ratios = [m["flash_ratio"] for m in all_metrics]

    # Calculate optimal values
    optimal_cuts = float(np.percentile(cuts_per_min, 75))
    optimal_clip = float(np.percentile(clip_lengths, 25))
    optimal_bright = float(np.mean(brightnesses))
    optimal_sat = float(np.mean(saturations))
    use_flash = float(np.mean(flash_ratios)) > 0.3

    # Determine pacing category
    if optimal_cuts > 30:
        pacing = "ultra_fast"
    elif optimal_cuts > 20:
        pacing = "aggressive"
    elif optimal_cuts > 12:
        pacing = "fast"
    else:
        pacing = "medium"

    # Determine color grade
    if optimal_bright > 140:
        color_grade = "bright_warm"
    elif optimal_bright > 110:
        color_grade = "cinematic"
    else:
        color_grade = "dark_dramatic"

    return {
        "learned_from_videos": len(all_metrics),
        "cuts_per_minute": optimal_cuts,
        "avg_clip_length": optimal_clip,
        "min_clip_length": max(0.8, optimal_clip * 0.5),
        "recommended_clip_length": optimal_clip,
        "transition_style": "flash" if use_flash else "hard_cut",
        "color_grade": color_grade,
        "brightness_level": optimal_bright,
        "contrast_level": 1.2,
        "saturation_level": optimal_sat / 128,
        "pacing": pacing,
        "uses_flash": use_flash,
        "flash_duration": 0.04,
        "vibe": "hype",
        "beat_sync_strength": "strong",
        "output_duration": 60,
    }

def print_intelligence_report(master, count):
    print(f"[KILLFRAME] ══════════════════════════════════════")
    print(f"[KILLFRAME]   AI LEARNING REPORT")
    print(f"[KILLFRAME] ══════════════════════════════════════")
    print(f"[KILLFRAME]   Videos analyzed    : {count}")
    print(f"[KILLFRAME]   Optimal cuts/min   : {master['cuts_per_minute']:.1f}")
    print(f"[KILLFRAME]   Optimal clip length: {master['avg_clip_length']:.2f}s")
    print(f"[KILLFRAME]   Color grade        : {master['color_grade']}")
    print(f"[KILLFRAME]   Pacing style       : {master['pacing']}")
    print(f"[KILLFRAME]   Uses flash cuts    : {master['uses_flash']}")
    print(f"[KILLFRAME]   Brightness level   : {master['brightness_level']:.0f}")
    print(f"[KILLFRAME] ══════════════════════════════════════")

def get_default_intelligence():
    return {
        "learned_from_videos": 0,
        "cuts_per_minute": 25,
        "avg_clip_length": 2.2,
        "min_clip_length": 1.0,
        "recommended_clip_length": 2.2,
        "transition_style": "flash",
        "color_grade": "bright_warm",
        "brightness_level": 135,
        "contrast_level": 1.15,
        "saturation_level": 1.2,
        "pacing": "aggressive",
        "uses_flash": True,
        "flash_duration": 0.04,
        "vibe": "hype",
        "beat_sync_strength": "strong",
        "output_duration": 60,
    }

def clear_cache():
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        print("[KILLFRAME] Learning cache cleared — will relearn on next run")
