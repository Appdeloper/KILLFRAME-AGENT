#!/usr/bin/env python3
import subprocess
import sys
import os
import argparse
import time
from dotenv import load_dotenv

# Auto-install missing packages
required = ["moviepy", "opencv-python", "numpy", "librosa", "scipy", "yt-dlp", "python-dotenv", "google-generativeai", "openai", "groq", "anthropic", "requests"]
for pkg in required:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
        print(f"[KILLFRAME] Installed: {pkg}")

load_dotenv()

from modules.style_analyzer import analyze_style
from modules.beat_detector import detect_beats
from modules.clip_selector import select_clips
from modules.video_editor import edit_video, cinematic_grade

def generate_thumbnail(output_path, style_profile):
    import cv2
    try:
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

            # Draw title text
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
    except Exception as e:
        print(f"[KILLFRAME] Thumbnail skip: {e}")

def main():
    parser = argparse.ArgumentParser(description="KILLFRAME-AGENT")
    parser.add_argument("--youtube", required=True)
    parser.add_argument("--footage", required=True)
    parser.add_argument("--music", default="")
    parser.add_argument("--output", default="killframe_output.mp4")
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()

    print("="*55)
    print("  KILLFRAME-AGENT — Autonomous Montage Editor")
    print("  Microsoft Agents League Hackathon 2026")
    print("="*55)
    print(f"  YouTube   : {args.youtube}")
    print(f"  Footage   : {args.footage}")
    print(f"  Music     : {args.music or 'Auto'}")
    print(f"  Duration  : {args.duration}s")
    print(f"  Output    : {args.output}")
    print("="*55)

    t0 = time.time()

    for attempt in range(3):
        try:
            print(f"\n[KILLFRAME] Attempt {attempt+1}/3")

            t1 = time.time()
            print("\n[KILLFRAME] Step 1/4 — Analyzing style...")
            style = analyze_style(args.youtube)
            style["output_duration"] = args.duration
            print(f"[KILLFRAME] Style done ({time.time()-t1:.1f}s)")

            music = args.music
            ref_song = style.get("reference_song_path","")
            if ref_song and os.path.exists(ref_song):
                music = ref_song
                print(f"[KILLFRAME] Using reference song: {ref_song}")
            elif args.music == "AUTO":
                if os.path.exists("real_music.mp3"):
                    music = "real_music.mp3"
                elif os.path.exists("test_music.mp3"):
                    music = "test_music.mp3"

            ref_video = style.get("reference_video_path","")

            t2 = time.time()
            print("\n[KILLFRAME] Step 2/4 — Detecting beats...")
            beats = detect_beats(music)
            print(f"[KILLFRAME] Beats done ({time.time()-t2:.1f}s)")
            style["recommended_clip_length"] = beats.get("avg_gap_seconds", 2.5)

            t3 = time.time()
            print("\n[KILLFRAME] Step 3/4 — Finding kills...")
            clips = select_clips(args.footage, style)
            print(f"[KILLFRAME] Kills done ({time.time()-t3:.1f}s)")

            if not clips:
                raise ValueError("No kill clips found")

            t4 = time.time()
            print(f"\n[KILLFRAME] Step 4/4 — Editing {len(clips)} clips...")
            edit_video(clips, beats, args.output, style, music, ref_video)
            print(f"[KILLFRAME] Edit done ({time.time()-t4:.1f}s)")

            if os.path.exists(args.output) and os.path.getsize(args.output) > 100000:
                mb = os.path.getsize(args.output)/(1024*1024)
                total = time.time()-t0
                print(f"\n[KILLFRAME] ✅ SUCCESS!")
                print(f"[KILLFRAME] Output : {args.output} ({mb:.1f}MB)")
                print(f"[KILLFRAME] Time   : {total:.1f}s")
                
                # Generate thumbnail as a bonus
                try:
                    generate_thumbnail(args.output, style)
                except Exception as e:
                    pass
                
                return
            raise ValueError("Output missing or too small")

        except Exception as e:
            print(f"[KILLFRAME] ❌ Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                print("[KILLFRAME] Retrying...")
                time.sleep(2)

    print("[KILLFRAME] ❌ All attempts failed")
    sys.exit(1)

if __name__ == "__main__":
    main()
