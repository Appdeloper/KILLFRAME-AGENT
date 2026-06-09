#!/usr/bin/env python3
"""
KILLFRAME-AGENT
Autonomous AI agent that watches, learns and edits
like a pro gaming content creator — automatically.
Microsoft Agents League Hackathon 2026
"""
import argparse
import sys
import os
import time
from dotenv import load_dotenv
load_dotenv()
from modules.style_analyzer import analyze_style
from modules.beat_detector import detect_beats
from modules.clip_selector import select_clips
from modules.video_editor import edit_video

def main():
    parser = argparse.ArgumentParser(description="KILLFRAME-AGENT — Autonomous Free Fire Montage Editor")
    parser.add_argument("--youtube", required=True, help="YouTube channel URL")
    parser.add_argument("--footage", required=True, help="Raw gameplay footage folder")
    parser.add_argument("--music", required=True, help="Background music MP3 path")
    parser.add_argument("--output", default="killframe_montage.mp4", help="Output MP4 path")
    args = parser.parse_args()
    print("=" * 50)
    print("  KILLFRAME-AGENT — Starting Pipeline")
    print("=" * 50)

    def set_progress(pct, msg=None):
        bar = f"[{pct:3d}%]"
        if msg:
            print(f"{bar} {msg}", flush=True)
        else:
            print(bar, flush=True)

    try:
        set_progress(5, "Initializing")
        time.sleep(0.15)

        set_progress(25, "Analyzing creator style...")
        style_profile = analyze_style(args.youtube)
        print(f"  Style profile: {style_profile}")
        time.sleep(0.1)

        set_progress(50, "Detecting beat timestamps...")
        beat_timeline = detect_beats(args.music)
        print(f"  Found {beat_timeline.get('total_beats', 0)} beats")
        time.sleep(0.1)

        set_progress(70, "Selecting kill highlights...")
        clips = select_clips(args.footage, style_profile)
        print(f"  Selected {len(clips)} clips")
        time.sleep(0.1)

        set_progress(90, "Editing final montage...")
        edit_video(clips, beat_timeline, args.output, style_profile)

        set_progress(100, f"Montage exported to {args.output}")
        print("=" * 50)
    except Exception as e:
        print(f"\n[KILLFRAME] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
