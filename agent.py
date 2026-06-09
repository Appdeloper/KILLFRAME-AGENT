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
    try:
        print("\n[KILLFRAME] Step 1/4 — Analyzing creator style...")
        style_profile = analyze_style(args.youtube)
        print(f"  Style profile: {style_profile}")
        print("\n[KILLFRAME] Step 2/4 — Detecting beat timestamps...")
        beat_timeline = detect_beats(args.music)
        print(f"  Found {beat_timeline['total_beats']} beats")
        print("\n[KILLFRAME] Step 3/4 — Selecting kill highlights...")
        clips = select_clips(args.footage, style_profile)
        print(f"  Selected {len(clips)} clips")
        print("\n[KILLFRAME] Step 4/4 — Editing final montage...")
        edit_video(clips, beat_timeline, args.output, style_profile)
        print(f"\n[KILLFRAME] Montage exported to {args.output}")
        print("=" * 50)
    except Exception as e:
        print(f"\n[KILLFRAME] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
