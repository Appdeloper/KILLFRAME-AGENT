#!/usr/bin/env python3
import subprocess
import sys

# Auto-install missing packages including scipy
required = ["moviepy", "opencv-python", "numpy", "librosa", "scipy", "yt-dlp", "python-dotenv", "google-generativeai", "openai", "groq", "anthropic"]
for pkg in required:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
        print(f"[KILLFRAME] Installed: {pkg}")

import argparse
import os
import time
import cv2
from dotenv import load_dotenv

load_dotenv()

# Imports from our modules
from modules.style_analyzer import analyze_style
from modules.beat_detector import detect_beats
from modules.clip_selector import select_clips
from modules.video_editor import edit_video, cinematic_grade
from modules.key_manager import get_api_key, validate_key

def generate_thumbnail(output_path, style_profile):
    # Get best frame from montage
    cap = cv2.VideoCapture(output_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
    ret, frame = cap.read()
    if ret:
        # Convert BGR (OpenCV read) to RGB for grading
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Apply thumbnail grading
        graded_rgb = cinematic_grade(rgb_frame, style_profile)
        # Convert back to BGR for OpenCV writing
        graded_bgr = cv2.cvtColor(graded_rgb, cv2.COLOR_RGB2BGR)

        # Draw title text (use DUPLEX/COMPLEX bold font fallback if IMPACT is missing)
        font = getattr(cv2, "FONT_HERSHEY_IMPACT", cv2.FONT_HERSHEY_DUPLEX)
        cv2.putText(graded_bgr, "KILLFRAME MONTAGE",
            (50, 80), font,
            2.5, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(graded_bgr, "FREE FIRE",
            (50, 160), font,
            3.5, (0, 0, 255), 5, cv2.LINE_AA)
        
        thumb_path = output_path.replace(".mp4", "_thumbnail.jpg")
        cv2.imwrite(thumb_path, graded_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[KILLFRAME] Thumbnail saved: {thumb_path}")
    cap.release()

def score_montage(output_path, beat_timeline, clips):
    score = 0
    if os.path.exists(output_path): score += 20
    if os.path.getsize(output_path) > 1000000: score += 20
    if len(clips) >= 8: score += 20
    if beat_timeline["total_beats"] > 0: score += 20
    if len(beat_timeline.get("bass_drops", [])) > 0: score += 20
    grade = "S+" if score == 100 else "S" if score >= 80 else "A" if score >= 60 else "B"
    print(f"[KILLFRAME] Montage Quality Score: {score}/100 — Grade: {grade}")
    return score

def main():
    # Reconfigure stdout to UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    # Load API key and validate
    api_key, provider = get_api_key()
    if not validate_key(api_key, provider):
        print("[KILLFRAME] Invalid API key. Please run again and enter a correct key.")
        sys.exit(1)

    # Set active key
    os.environ[f"{provider.upper()}_API_KEY"] = api_key

    parser = argparse.ArgumentParser(description="KILLFRAME-AGENT - Hollywood Level Montage Editor")
    parser.add_argument("--youtube", required=True, help="YouTube reference video URL")
    parser.add_argument("--footage", required=True, help="Path to raw footage folder or file")
    parser.add_argument("--music", required=True, help="Path to background music file")
    parser.add_argument("--output", default="killframe_montage.mp4", help="Path to output final montage")
    args = parser.parse_args()

    print("=" * 55)
    print("  KILLFRAME-AGENT - Starting Professional Montage Pipeline")
    print("=" * 55)

    t0 = time.time()

    try:
        # Step 1: Style Analysis
        t_step = time.time()
        print("\n[KILLFRAME] Step 1/4 - Analyzing creator style via Deep AI...")
        style_profile = analyze_style(args.youtube)
        print(f"[KILLFRAME] Step completed in {time.time() - t_step:.1f}s")

        # Step 2: Beat Detection
        t_step = time.time()
        print("\n[KILLFRAME] Step 2/4 - Performing HPSS stem separation and beat analysis...")
        beat_timeline = detect_beats(args.music)
        print(f"[KILLFRAME] Step completed in {time.time() - t_step:.1f}s")

        # Step 3: Clip Selection
        t_step = time.time()
        print("\n[KILLFRAME] Step 3/4 - Running 7-signal Military Grade Kill Detection...")
        clips = select_clips(args.footage, style_profile)
        print(f"[KILLFRAME] Step completed in {time.time() - t_step:.1f}s")

        # Step 4: Render Video
        t_step = time.time()
        print("\n[KILLFRAME] Step 4/4 - Rendering Cinematic Hollywood Montage at 60fps...")
        edit_video(clips, beat_timeline, args.output, style_profile, args.music)
        print(f"[KILLFRAME] Step completed in {time.time() - t_step:.1f}s")

        # Step 5: Thumbnail Generation
        t_step = time.time()
        print("\n[KILLFRAME] Generating Video Thumbnail...")
        generate_thumbnail(args.output, style_profile)
        print(f"[KILLFRAME] Step completed in {time.time() - t_step:.1f}s")

        # Step 6: Quality Scorer
        t_step = time.time()
        print("\n[KILLFRAME] Running Montage Quality Scorer...")
        score_montage(args.output, beat_timeline, clips)
        print(f"[KILLFRAME] Step completed in {time.time() - t_step:.1f}s")

        # Conclude pipeline
        total_time = time.time() - t0
        print("\n" + "=" * 55)
        print(f"[KILLFRAME] Success: Montage and thumbnail exported.")
        print(f"[KILLFRAME] Total pipeline time: {total_time:.1f}s")
        print("=" * 55)

    except Exception as e:
        print(f"\n[KILLFRAME] [FATAL ERROR] Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
