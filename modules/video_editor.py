import os
import cv2
import numpy as np
import logging
from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, concatenate_videoclips, CompositeVideoClip, TextClip, ImageClip
from moviepy.audio.AudioClip import concatenate_audioclips
import moviepy.video.fx.all as vfx
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cinematic_grade(frame, style_profile):
    try:
        f = frame.astype(np.float32)
        # Subtle contrast only 1.15x not 1.35x
        f = np.clip((f - 128) * 1.15 + 128, 0, 255)
        # Convert to HSV for saturation
        hsv = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        # Boost saturation only 1.2x not 1.45x
        hsv[:,:,1] = np.clip(hsv[:,:,1] * 1.2, 0, 255)
        f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
        # Very subtle vignette 0.15 not 0.5
        h, w = f.shape[:2]
        Y, X = np.ogrid[:h, :w]
        v = 1 - 0.15*(((X-w/2)**2+(Y-h/2)**2)/((w/2)**2+(h/2)**2))
        v = np.clip(v, 0.85, 1.0)
        f = (f * v[:,:,np.newaxis])
        return np.clip(f, 0, 255).astype(np.uint8)
    except:
        return frame

def edit_video(clips, beat_timeline, output_path, style_profile, music_path):
    from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, ColorClip, CompositeVideoClip, concatenate_audioclips
    import moviepy.video.fx.all as vfx

    print(f"[KILLFRAME] Loading {len(clips)} clips...")
    loaded = []
    for i, path in enumerate(clips):
        try:
            clip_path = path["path"] if isinstance(path, dict) else path
            if not os.path.exists(clip_path):
                print(f"[KILLFRAME] Missing: {clip_path}")
                continue
            c = VideoFileClip(clip_path)
            if c.duration < 0.1:
                continue
            # Trim to beat length
            clip_len = min(float(beat_timeline.get("recommended_clip_length", 2.5)), c.duration)
            c = c.subclip(0, clip_len)
            # Resize to 1080p
            c = c.resize((1920, 1080))
            # Apply SUBTLE color grade
            c = c.fl_image(lambda f: cinematic_grade(f, style_profile))
            loaded.append(c)
            print(f"[KILLFRAME] Loaded clip {i+1}/{len(clips)}: {clip_len:.1f}s")
        except Exception as e:
            print(f"[KILLFRAME] Skip clip {i+1}: {e}")

    if not loaded:
        print("[KILLFRAME] ERROR: No clips loaded!")
        raise ValueError("No valid clips loaded for video editing.")

    print(f"[KILLFRAME] Building montage from {len(loaded)} clips...")

    # White flash between clips — EXACTLY like reference video
    final_clips = []
    for i, clip in enumerate(loaded):
        final_clips.append(clip)
        if i < len(loaded) - 1:
            flash = ColorClip(
                size=(1920, 1080),
                color=[255, 255, 255],
                duration=0.04
            )
            final_clips.append(flash)

    final_video = concatenate_videoclips(final_clips, method="compose")
    print(f"[KILLFRAME] Montage duration: {final_video.duration:.1f}s")

    if music_path and os.path.exists(music_path):
        try:
            audio = AudioFileClip(music_path)
            print(f"[KILLFRAME] Music loaded: {audio.duration:.1f}s")
            # Loop if needed
            if audio.duration < final_video.duration:
                times = int(final_video.duration / audio.duration) + 1
                audio = concatenate_audioclips([audio] * times)
            audio = audio.subclip(0, final_video.duration)
            audio = audio.volumex(0.85)
            final_video = final_video.set_audio(audio)
            print("[KILLFRAME] Music synced successfully")
        except Exception as e:
            print(f"[KILLFRAME] Music error: {e}")

    try:
        print(f"[KILLFRAME] Exporting to {output_path}...")
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            fps=30,
            threads=4,
            preset="fast",
            logger=None
        )
        if os.path.exists(output_path):
            mb = os.path.getsize(output_path) / (1024*1024)
            print(f"[KILLFRAME] Export complete: {mb:.1f}MB")
        else:
            print("[KILLFRAME] ERROR: Output file not created!")
    except Exception as e:
        print(f"[KILLFRAME] Export error: {e}")
    finally:
        for c in loaded:
            try: c.close()
            except: pass
