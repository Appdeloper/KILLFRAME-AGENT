#!/usr/bin/env python3
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
    parser = argparse.ArgumentParser(description="KILLFRAME-AGENT")
    parser.add_argument("--youtube", required=True)
    parser.add_argument("--footage", required=True)
    parser.add_argument("--music", required=True)
    parser.add_argument("--output", default="killframe_montage.mp4")
    args = parser.parse_args()
    
    print("="*50)
    print("  KILLFRAME-AGENT - Starting Pipeline")
    print("="*50)
    
    pipeline_start = time.time()
    
    try:
        # Step 1
        t_start = time.time()
        print("\n[KILLFRAME] Step 1/4 - Analyzing creator style...")
        style_profile = analyze_style(args.youtube)
        print(f"  Style profile: {style_profile}")
        print(f"  Step 1 completed in {time.time() - t_start:.2f} seconds")
        
        # Step 2
        t_start = time.time()
        print("\n[KILLFRAME] Step 2/4 - Detecting beat timestamps...")
        beat_timeline = detect_beats(args.music)
        print(f"  Found {beat_timeline['total_beats']} beats")
        print(f"  Step 2 completed in {time.time() - t_start:.2f} seconds")
        
        # Step 3
        t_start = time.time()
        print("\n[KILLFRAME] Step 3/4 - Selecting kill highlights...")
        clips = select_clips(args.footage, style_profile)
        print(f"  Selected {len(clips)} clips")
        print(f"  Step 3 completed in {time.time() - t_start:.2f} seconds")
        
        # Step 4
        t_start = time.time()
        print("\n[KILLFRAME] Step 4/4 - Editing final montage...")
        edit_video(clips, beat_timeline, args.output, style_profile, args.music)
        print(f"  Step 4 completed in {time.time() - t_start:.2f} seconds")
        
        print(f"\n[KILLFRAME] Montage exported to {args.output}")
        print(f"  Total pipeline completed in {time.time() - pipeline_start:.2f} seconds")
        print("="*50)
        
    except Exception as e:
        print(f"\n[KILLFRAME] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
